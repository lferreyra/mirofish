"""
图谱相关API路由
采用项目上下文机制，服务端持久化状态
"""

import os
import json
import time
import uuid
import traceback
import threading
from flask import request, jsonify

from . import graph_bp
from ..config import Config
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..services.simulation_manager import SimulationManager, SimulationStatus
from ..services.simulation_runner import SimulationRunner
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus

# 获取日志器
logger = get_logger('mirofish.api')


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


def _build_pipeline_project_name(seed_data: dict, config: dict) -> str:
    """构建管道项目名称"""
    raw_name = (
        ((seed_data or {}).get('marketContext') or {}).get('query')
        or config.get('scenario_description')
        or config.get('time_horizon')
        or 'Oracle scenario'
    )
    normalized = str(raw_name).replace('\n', ' ').strip()
    suffix = normalized[:64] or 'Oracle scenario'
    return f"DreamWard Oracle - {suffix}"


def _build_pipeline_simulation_requirement(seed_data: dict, config: dict) -> str:
    """构建模拟需求描述"""
    scenario_query = (
        config.get('scenario_description')
        or ((seed_data or {}).get('marketContext') or {}).get('query')
        or 'Oraklet-simulering'
    )
    horizon = config.get('time_horizon') or 'ukjent horisont'
    rounds = config.get('rounds') or '未知'
    return (
        f"{scenario_query}. "
        f"Kjør simuleringen over {horizon} med {rounds} runder "
        f"basert på den opplastede DreamWard-porteføljedokumentasjonen."
    )


def _build_pipeline_document(seed_data: dict, config: dict) -> str:
    """将 DreamWard seed_data 转换为 MiroFish 可处理的 Markdown 文档"""
    properties = seed_data.get('properties') or []
    market_context = seed_data.get('marketContext') or {}
    regulatory_context = seed_data.get('regulatoryContext') or {}
    demographic_data = seed_data.get('demographicData') or {}
    agent_profiles = seed_data.get('agentProfiles') or []

    payload = {
        "scenario": {
            "query": market_context.get('query') or config.get('scenario_description'),
            "time_horizon": config.get('time_horizon'),
            "rounds": config.get('rounds'),
            "entity_types": config.get('entity_types') or [],
            "agents": config.get('agents'),
        },
        "properties": properties,
        "market_context": market_context,
        "regulatory_context": regulatory_context,
        "demographic_data": demographic_data,
        "agent_profiles": agent_profiles,
        "metadata": seed_data.get('metadata') or {},
    }

    property_lines = []
    for index, prop in enumerate(properties, start=1):
        parts = [
            prop.get('address'),
            prop.get('city'),
            prop.get('propertyType'),
            f"leie {prop.get('monthlyRentNok')} NOK/mnd" if prop.get('monthlyRentNok') else None,
            f"verdi {prop.get('currentValueNok')} NOK" if prop.get('currentValueNok') else None,
            f"{prop.get('sizeSqm')} kvm" if prop.get('sizeSqm') else None,
        ]
        property_lines.append(f"{index}. {' • '.join([str(p) for p in parts if p])}")

    return "\n".join([
        '# DreamWard Oracle provisioning dossier',
        '',
        'Denne filen er generert av DreamWard for å opprette et MiroFish-prosjekt, generere ontologi og bygge en graph-backed simulering.',
        '',
        '## Scenario',
        f"- Query: {market_context.get('query') or config.get('scenario_description') or 'Ukjent'}",
        f"- Tidshorisont: {config.get('time_horizon') or 'Ukjent'}",
        f"- Runder: {config.get('rounds') or 'Ukjent'}",
        f"- Ønskede entitetstyper: {', '.join(config.get('entity_types') or []) or 'Ikke spesifisert'}",
        '',
        '## Eiendommer',
        *(property_lines if property_lines else ['- Ingen eiendommer i seed_data.']),
        '',
        '## Full strukturert kontekst (JSON)',
        '```json',
        json.dumps(payload, ensure_ascii=False, indent=2),
        '```',
        '',
    ])


def _resolve_parallel_profile_count(agents_config) -> int:
    """根据配置推导 prepare 阶段的并行 profile 生成数"""
    if isinstance(agents_config, int):
        raw_count = agents_config
    elif isinstance(agents_config, list):
        raw_count = len(agents_config)
    else:
        raw_count = 1
    return max(1, min(5, raw_count or 1))


def _update_pipeline_task(
    task_manager: TaskManager,
    task_id: str,
    phase: str,
    status: TaskStatus = None,
    progress: int = None,
    message: str = None,
    result: dict = None,
    error: str = None,
    project_id: str = None,
    graph_task_id: str = None,
    job_id: str = None,
):
    """更新 pipeline 任务状态并附带阶段详情"""
    progress_detail = {
        "phase": phase,
        "project_id": project_id,
        "graph_task_id": graph_task_id,
        "job_id": job_id,
    }
    task_manager.update_task(
        task_id,
        status=status,
        progress=progress,
        message=message,
        result=result,
        error=error,
        progress_detail=progress_detail,
    )


def _find_pipeline_task_by_pipeline_id(pipeline_id: str):
    """根据 pipeline_id 查找任务"""
    task_manager = TaskManager()
    for task in task_manager.list_tasks(task_type="graph_pipeline"):
        metadata = (task or {}).get('metadata') or {}
        if metadata.get('pipeline_id') == pipeline_id:
            return task
    return None


# ============== 项目管理接口 ==============

@graph_bp.route('/project/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """
    获取项目详情
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": f"项目不存在: {project_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": project.to_dict()
    })


@graph_bp.route('/project/list', methods=['GET'])
def list_projects():
    """
    列出所有项目
    """
    limit = request.args.get('limit', 50, type=int)
    projects = ProjectManager.list_projects(limit=limit)
    
    return jsonify({
        "success": True,
        "data": [p.to_dict() for p in projects],
        "count": len(projects)
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """
    删除项目
    """
    success = ProjectManager.delete_project(project_id)
    
    if not success:
        return jsonify({
            "success": False,
            "error": f"项目不存在或删除失败: {project_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "message": f"项目已删除: {project_id}"
    })


@graph_bp.route('/project/<project_id>/reset', methods=['POST'])
def reset_project(project_id: str):
    """
    重置项目状态（用于重新构建图谱）
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": f"项目不存在: {project_id}"
        }), 404
    
    # 重置到本体已生成状态
    if project.ontology:
        project.status = ProjectStatus.ONTOLOGY_GENERATED
    else:
        project.status = ProjectStatus.CREATED
    
    project.graph_id = None
    project.graph_build_task_id = None
    project.error = None
    ProjectManager.save_project(project)
    
    return jsonify({
        "success": True,
        "message": f"项目已重置: {project_id}",
        "data": project.to_dict()
    })


# ============== 接口1：上传文件并生成本体 ==============

@graph_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    """
    接口1：上传文件，分析生成本体定义
    
    请求方式：multipart/form-data
    
    参数：
        files: 上传的文件（PDF/MD/TXT），可多个
        simulation_requirement: 模拟需求描述（必填）
        project_name: 项目名称（可选）
        additional_context: 额外说明（可选）
        
    返回：
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "ontology": {
                    "entity_types": [...],
                    "edge_types": [...],
                    "analysis_summary": "..."
                },
                "files": [...],
                "total_text_length": 12345
            }
        }
    """
    try:
        logger.info("=== 开始生成本体定义 ===")
        
        # 获取参数
        simulation_requirement = request.form.get('simulation_requirement', '')
        project_name = request.form.get('project_name', 'Unnamed Project')
        additional_context = request.form.get('additional_context', '')
        
        logger.debug(f"项目名称: {project_name}")
        logger.debug(f"模拟需求: {simulation_requirement[:100]}...")
        
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": "请提供模拟需求描述 (simulation_requirement)"
            }), 400
        
        # 获取上传的文件
        uploaded_files = request.files.getlist('files')
        if not uploaded_files or all(not f.filename for f in uploaded_files):
            return jsonify({
                "success": False,
                "error": "请至少上传一个文档文件"
            }), 400
        
        # 创建项目
        project = ProjectManager.create_project(name=project_name)
        project.simulation_requirement = simulation_requirement
        logger.info(f"创建项目: {project.project_id}")
        
        # 保存文件并提取文本
        document_texts = []
        all_text = ""
        
        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                # 保存文件到项目目录
                file_info = ProjectManager.save_file_to_project(
                    project.project_id, 
                    file, 
                    file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "size": file_info["size"]
                })
                
                # 提取文本
                text = FileParser.extract_text(file_info["path"])
                text = TextProcessor.preprocess_text(text)
                document_texts.append(text)
                all_text += f"\n\n=== {file_info['original_filename']} ===\n{text}"
        
        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            return jsonify({
                "success": False,
                "error": "没有成功处理任何文档，请检查文件格式"
            }), 400
        
        # 保存提取的文本
        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        logger.info(f"文本提取完成，共 {len(all_text)} 字符")
        
        # 生成本体
        logger.info("调用 LLM 生成本体定义...")
        generator = OntologyGenerator()
        ontology = generator.generate(
            document_texts=document_texts,
            simulation_requirement=simulation_requirement,
            additional_context=additional_context if additional_context else None
        )
        
        # 保存本体到项目
        entity_count = len(ontology.get("entity_types", []))
        edge_count = len(ontology.get("edge_types", []))
        logger.info(f"本体生成完成: {entity_count} 个实体类型, {edge_count} 个关系类型")
        
        project.ontology = {
            "entity_types": ontology.get("entity_types", []),
            "edge_types": ontology.get("edge_types", [])
        }
        project.analysis_summary = ontology.get("analysis_summary", "")
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        ProjectManager.save_project(project)
        logger.info(f"=== 本体生成完成 === 项目ID: {project.project_id}")
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project.project_id,
                "project_name": project.name,
                "ontology": project.ontology,
                "analysis_summary": project.analysis_summary,
                "files": project.files,
                "total_text_length": project.total_text_length
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 接口2：构建图谱 ==============

@graph_bp.route('/build', methods=['POST'])
def build_graph():
    """
    接口2：根据project_id构建图谱
    
    请求（JSON）：
        {
            "project_id": "proj_xxxx",  // 必填，来自接口1
            "graph_name": "图谱名称",    // 可选
            "chunk_size": 500,          // 可选，默认500
            "chunk_overlap": 50         // 可选，默认50
        }
        
    返回：
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "task_id": "task_xxxx",
                "message": "图谱构建任务已启动"
            }
        }
    """
    try:
        logger.info("=== 开始构建图谱 ===")
        
        # 检查配置
        errors = []
        if not Config.ZEP_API_KEY:
            errors.append("ZEP_API_KEY未配置")
        if errors:
            logger.error(f"配置错误: {errors}")
            return jsonify({
                "success": False,
                "error": "配置错误: " + "; ".join(errors)
            }), 500
        
        # 解析请求
        data = request.get_json() or {}
        project_id = data.get('project_id')
        logger.debug(f"请求参数: project_id={project_id}")
        
        if not project_id:
            return jsonify({
                "success": False,
                "error": "请提供 project_id"
            }), 400
        
        # 获取项目
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": f"项目不存在: {project_id}"
            }), 404
        
        # 检查项目状态
        force = data.get('force', False)  # 强制重新构建
        
        if project.status == ProjectStatus.CREATED:
            return jsonify({
                "success": False,
                "error": "项目尚未生成本体，请先调用 /ontology/generate"
            }), 400
        
        if project.status == ProjectStatus.GRAPH_BUILDING and not force:
            return jsonify({
                "success": False,
                "error": "图谱正在构建中，请勿重复提交。如需强制重建，请添加 force: true",
                "task_id": project.graph_build_task_id
            }), 400
        
        # 如果强制重建，重置状态
        if force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None
        
        # 获取配置
        graph_name = data.get('graph_name', project.name or 'MiroFish Graph')
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)
        
        # 更新项目配置
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap
        
        # 获取提取的文本
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            return jsonify({
                "success": False,
                "error": "未找到提取的文本内容"
            }), 400
        
        # 获取本体
        ontology = project.ontology
        if not ontology:
            return jsonify({
                "success": False,
                "error": "未找到本体定义"
            }), 400
        
        # 创建异步任务
        task_manager = TaskManager()
        task_id = task_manager.create_task(f"构建图谱: {graph_name}")
        logger.info(f"创建图谱构建任务: task_id={task_id}, project_id={project_id}")
        
        # 更新项目状态
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)
        
        # 启动后台任务
        def build_task():
            build_logger = get_logger('mirofish.build')
            try:
                build_logger.info(f"[{task_id}] 开始构建图谱...")
                task_manager.update_task(
                    task_id, 
                    status=TaskStatus.PROCESSING,
                    message="初始化图谱构建服务..."
                )
                
                # 创建图谱构建服务
                builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
                
                # 分块
                task_manager.update_task(
                    task_id,
                    message="文本分块中...",
                    progress=5
                )
                chunks = TextProcessor.split_text(
                    text, 
                    chunk_size=chunk_size, 
                    overlap=chunk_overlap
                )
                total_chunks = len(chunks)
                
                # 创建图谱
                task_manager.update_task(
                    task_id,
                    message="创建Zep图谱...",
                    progress=10
                )
                graph_id = builder.create_graph(name=graph_name)
                
                # 更新项目的graph_id
                project.graph_id = graph_id
                ProjectManager.save_project(project)
                
                # 设置本体
                task_manager.update_task(
                    task_id,
                    message="设置本体定义...",
                    progress=15
                )
                builder.set_ontology(graph_id, ontology)
                
                # 添加文本（progress_callback 签名是 (msg, progress_ratio)）
                def add_progress_callback(msg, progress_ratio):
                    progress = 15 + int(progress_ratio * 40)  # 15% - 55%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )
                
                task_manager.update_task(
                    task_id,
                    message=f"开始添加 {total_chunks} 个文本块...",
                    progress=15
                )
                
                episode_uuids = builder.add_text_batches(
                    graph_id, 
                    chunks,
                    batch_size=3,
                    progress_callback=add_progress_callback
                )
                
                # 等待Zep处理完成（查询每个episode的processed状态）
                task_manager.update_task(
                    task_id,
                    message="等待Zep处理数据...",
                    progress=55
                )
                
                def wait_progress_callback(msg, progress_ratio):
                    progress = 55 + int(progress_ratio * 35)  # 55% - 90%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )
                
                builder._wait_for_episodes(episode_uuids, wait_progress_callback)
                
                # 获取图谱数据
                task_manager.update_task(
                    task_id,
                    message="获取图谱数据...",
                    progress=95
                )
                graph_data = builder.get_graph_data(graph_id)
                
                # 更新项目状态
                project.status = ProjectStatus.GRAPH_COMPLETED
                ProjectManager.save_project(project)
                
                node_count = graph_data.get("node_count", 0)
                edge_count = graph_data.get("edge_count", 0)
                build_logger.info(f"[{task_id}] 图谱构建完成: graph_id={graph_id}, 节点={node_count}, 边={edge_count}")
                
                # 完成
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message="图谱构建完成",
                    progress=100,
                    result={
                        "project_id": project_id,
                        "graph_id": graph_id,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks
                    }
                )
                
            except Exception as e:
                # 更新项目状态为失败
                build_logger.error(f"[{task_id}] 图谱构建失败: {str(e)}")
                build_logger.debug(traceback.format_exc())
                
                project.status = ProjectStatus.FAILED
                project.error = str(e)
                ProjectManager.save_project(project)
                
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=f"构建失败: {str(e)}",
                    error=traceback.format_exc()
                )
        
        # 启动后台线程
        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "task_id": task_id,
                "message": "图谱构建任务已启动，请通过 /task/{task_id} 查询进度"
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/pipeline/provision-and-start', methods=['POST'])
def provision_and_start():
    """
    Full pipeline: ontology → graph build → simulation create → prepare → start.
    Runs in background thread, returns immediately with task tracking.
    """
    try:
        logger.info("=== 开始启动全流程 pipeline ===")

        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "配置错误: ZEP_API_KEY未配置"
            }), 500

        data = request.get_json() or {}
        seed_data = data.get('seed_data')
        config = data.get('config') or {}

        if not isinstance(seed_data, dict):
            return jsonify({
                "success": False,
                "error": "请提供 seed_data 对象"
            }), 400

        if not isinstance(config, dict):
            return jsonify({
                "success": False,
                "error": "请提供 config 对象"
            }), 400

        rounds = config.get('rounds')
        if rounds is not None:
            try:
                rounds = int(rounds)
                if rounds <= 0:
                    raise ValueError()
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "error": "config.rounds 必须是正整数"
                }), 400
            config['rounds'] = rounds

        agents_config = config.get('agents')
        if isinstance(agents_config, int) and agents_config <= 0:
            return jsonify({
                "success": False,
                "error": "config.agents 必须是正整数"
            }), 400

        entity_types = config.get('entity_types')
        if entity_types is not None:
            if not isinstance(entity_types, list):
                return jsonify({
                    "success": False,
                    "error": "config.entity_types 必须是字符串数组"
                }), 400
            config['entity_types'] = [str(entity_type).strip() for entity_type in entity_types if str(entity_type).strip()]

        pipeline_id = str(uuid.uuid4())
        project_name = _build_pipeline_project_name(seed_data, config)
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="graph_pipeline",
            metadata={
                "pipeline_id": pipeline_id,
                "project_name": project_name,
            }
        )

        def pipeline_task():
            pipeline_logger = get_logger('mirofish.pipeline')
            project = None
            project_id = None
            graph_task_id = None
            graph_id = None
            simulation_id = None
            simulation_manager = SimulationManager()

            try:
                pipeline_logger.info(f"[{pipeline_id}] Pipeline started")
                _update_pipeline_task(
                    task_manager,
                    task_id,
                    phase="ontology_generation",
                    status=TaskStatus.PROCESSING,
                    progress=10,
                    message="Generating ontology..."
                )

                project = ProjectManager.create_project(name=project_name)
                project_id = project.project_id
                project.simulation_requirement = _build_pipeline_simulation_requirement(seed_data, config)

                provisioning_document = _build_pipeline_document(seed_data, config)
                processed_text = TextProcessor.preprocess_text(provisioning_document)

                project.total_text_length = len(processed_text)
                project.files = [{
                    "filename": "dreamward-oracle-brief.md",
                    "size": len(provisioning_document.encode('utf-8'))
                }]
                ProjectManager.save_extracted_text(project_id, processed_text)

                files_dir = ProjectManager._get_project_files_dir(project_id)
                os.makedirs(files_dir, exist_ok=True)
                brief_path = os.path.join(files_dir, 'dreamward-oracle-brief.md')
                with open(brief_path, 'w', encoding='utf-8') as f:
                    f.write(provisioning_document)

                ProjectManager.save_project(project)
                pipeline_logger.info(f"[{pipeline_id}] Phase 1/4 ontology generation: project_id={project_id}")

                ontology = OntologyGenerator().generate(
                    document_texts=[processed_text],
                    simulation_requirement=project.simulation_requirement,
                    additional_context=(
                        "DreamWard Oracle generated this dossier from structured property, tenant, market, "
                        "and scenario data. Use it as the authoritative source when deriving the ontology "
                        "and building the graph."
                    )
                )

                project.ontology = {
                    "entity_types": ontology.get("entity_types", []),
                    "edge_types": ontology.get("edge_types", [])
                }
                project.analysis_summary = ontology.get("analysis_summary", "")
                project.status = ProjectStatus.ONTOLOGY_GENERATED
                ProjectManager.save_project(project)

                pipeline_logger.info(f"[{pipeline_id}] Phase 2/4 graph building")
                _update_pipeline_task(
                    task_manager,
                    task_id,
                    phase="graph_building",
                    progress=30,
                    message="Building knowledge graph...",
                    project_id=project_id
                )

                builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
                graph_task_id = builder.build_graph_async(
                    text=processed_text,
                    ontology=project.ontology,
                    graph_name=project.name or 'MiroFish Graph',
                    chunk_size=project.chunk_size or Config.DEFAULT_CHUNK_SIZE,
                    chunk_overlap=project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP,
                    batch_size=3
                )

                project.status = ProjectStatus.GRAPH_BUILDING
                project.graph_build_task_id = graph_task_id
                ProjectManager.save_project(project)

                while True:
                    graph_task = task_manager.get_task(graph_task_id)
                    if not graph_task:
                        raise RuntimeError(f"图谱构建任务不存在: {graph_task_id}")

                    graph_progress = max(0, min(graph_task.progress or 0, 100))
                    pipeline_progress = 30 + int(graph_progress * 0.4)
                    _update_pipeline_task(
                        task_manager,
                        task_id,
                        phase="graph_building",
                        progress=pipeline_progress,
                        message=graph_task.message or "Building knowledge graph...",
                        project_id=project_id,
                        graph_task_id=graph_task_id
                    )

                    if graph_task.status == TaskStatus.COMPLETED:
                        graph_result = graph_task.result or {}
                        graph_id = graph_result.get('graph_id')
                        if not graph_id:
                            raise RuntimeError("图谱构建完成但未返回 graph_id")
                        project.graph_id = graph_id
                        project.status = ProjectStatus.GRAPH_COMPLETED
                        ProjectManager.save_project(project)
                        break

                    if graph_task.status == TaskStatus.FAILED:
                        raise RuntimeError(graph_task.message or graph_task.error or "图谱构建失败")

                    time.sleep(2)

                pipeline_logger.info(f"[{pipeline_id}] Phase 3/4 simulation setup: graph_id={graph_id}")
                _update_pipeline_task(
                    task_manager,
                    task_id,
                    phase="simulation_setup",
                    progress=70,
                    message="Preparing simulation agents...",
                    project_id=project_id,
                    graph_task_id=graph_task_id
                )

                simulation_state = simulation_manager.create_simulation(
                    project_id=project_id,
                    graph_id=graph_id,
                    enable_twitter=True,
                    enable_reddit=True,
                )
                simulation_id = simulation_state.simulation_id

                def prepare_progress_callback(stage, progress, message, **kwargs):
                    pipeline_progress = 70 + min(9, int(max(0, min(progress, 100)) / 10))
                    _update_pipeline_task(
                        task_manager,
                        task_id,
                        phase="simulation_setup",
                        progress=pipeline_progress,
                        message=message or "Preparing simulation agents...",
                        project_id=project_id,
                        graph_task_id=graph_task_id,
                        job_id=simulation_id
                    )

                prepared_state = simulation_manager.prepare_simulation(
                    simulation_id=simulation_id,
                    simulation_requirement=project.simulation_requirement or "",
                    document_text=processed_text,
                    defined_entity_types=config.get('entity_types'),
                    use_llm_for_profiles=True,
                    progress_callback=prepare_progress_callback,
                    parallel_profile_count=_resolve_parallel_profile_count(agents_config)
                )

                if prepared_state.status != SimulationStatus.READY:
                    raise RuntimeError(prepared_state.error or f"模拟准备未完成: {prepared_state.status.value}")

                pipeline_logger.info(f"[{pipeline_id}] Phase 4/4 simulation start: simulation_id={simulation_id}")
                _update_pipeline_task(
                    task_manager,
                    task_id,
                    phase="simulation_running",
                    progress=80,
                    message="Simulation running...",
                    project_id=project_id,
                    graph_task_id=graph_task_id,
                    job_id=simulation_id
                )

                SimulationRunner.start_simulation(
                    simulation_id=simulation_id,
                    platform='parallel',
                    max_rounds=config.get('rounds'),
                    enable_graph_memory_update=False,
                    graph_id=None
                )

                latest_state = simulation_manager.get_simulation(simulation_id)
                if latest_state:
                    latest_state.status = SimulationStatus.RUNNING
                    simulation_manager._save_simulation_state(latest_state)

                _update_pipeline_task(
                    task_manager,
                    task_id,
                    phase="completed",
                    status=TaskStatus.COMPLETED,
                    progress=100,
                    message="Pipeline completed",
                    result={
                        "job_id": simulation_id,
                        "project_id": project_id,
                        "graph_id": graph_id,
                    },
                    project_id=project_id,
                    graph_task_id=graph_task_id,
                    job_id=simulation_id
                )
                pipeline_logger.info(f"[{pipeline_id}] Pipeline completed: job_id={simulation_id}")

            except Exception as e:
                pipeline_logger.error(f"[{pipeline_id}] Pipeline failed: {str(e)}")
                pipeline_logger.debug(traceback.format_exc())

                if project:
                    project.status = ProjectStatus.FAILED
                    project.error = str(e)
                    ProjectManager.save_project(project)

                if simulation_id:
                    latest_state = simulation_manager.get_simulation(simulation_id)
                    if latest_state:
                        latest_state.status = SimulationStatus.FAILED
                        latest_state.error = str(e)
                        simulation_manager._save_simulation_state(latest_state)

                _update_pipeline_task(
                    task_manager,
                    task_id,
                    phase="failed",
                    status=TaskStatus.FAILED,
                    message=f"Pipeline failed: {str(e)}",
                    error=traceback.format_exc(),
                    project_id=project_id,
                    graph_task_id=graph_task_id,
                    job_id=simulation_id
                )

        thread = threading.Thread(target=pipeline_task, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "pipeline_id": pipeline_id,
                "task_id": task_id,
                "message": "Pipeline started"
            }
        })

    except Exception as e:
        logger.error(f"启动 pipeline 失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/pipeline/status/<pipeline_id>', methods=['GET'])
def get_pipeline_status(pipeline_id: str):
    """查询 pipeline 状态"""
    task = _find_pipeline_task_by_pipeline_id(pipeline_id)

    if not task:
        return jsonify({
            "success": False,
            "error": f"Pipeline 不存在: {pipeline_id}"
        }), 404

    progress_detail = task.get('progress_detail') or {}
    result = task.get('result')
    job_id = None
    if isinstance(result, dict):
        job_id = result.get('job_id')
    if not job_id:
        job_id = progress_detail.get('job_id')

    status = task.get('status')
    if status == TaskStatus.PROCESSING.value:
        status = 'running'

    return jsonify({
        "success": True,
        "data": {
            "pipeline_id": pipeline_id,
            "task_id": task.get('task_id'),
            "status": status,
            "phase": progress_detail.get('phase', 'pending'),
            "progress": task.get('progress', 0),
            "message": task.get('message', ''),
            "job_id": job_id,
            "result": result,
        }
    })


# ============== 任务查询接口 ==============

@graph_bp.route('/task/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """
    查询任务状态
    """
    task = TaskManager().get_task(task_id)
    
    if not task:
        return jsonify({
            "success": False,
            "error": f"任务不存在: {task_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": task.to_dict()
    })


@graph_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """
    列出所有任务
    """
    tasks = TaskManager().list_tasks()
    
    return jsonify({
        "success": True,
        "data": [t.to_dict() for t in tasks],
        "count": len(tasks)
    })


# ============== 图谱数据接口 ==============

@graph_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id: str):
    """
    获取图谱数据（节点和边）
    """
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY未配置"
            }), 500
        
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        graph_data = builder.get_graph_data(graph_id)
        
        return jsonify({
            "success": True,
            "data": graph_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/delete/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id: str):
    """
    删除Zep图谱
    """
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY未配置"
            }), 500
        
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        builder.delete_graph(graph_id)
        
        return jsonify({
            "success": True,
            "message": f"图谱已删除: {graph_id}"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
