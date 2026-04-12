"""
AUGUR Agent Preview — Endpoints para preview e customização de agentes.

Adicionar ao final de backend/app/api/simulation.py

Endpoints:
  POST /api/simulation/preview-agents   — Gera preview dos agentes para aprovação
  POST /api/simulation/custom-agent     — Gera perfil completo a partir de descrição livre
  POST /api/simulation/approve-agents   — Salva lista aprovada de agentes
"""

# ============================================================
# ADICIONAR AO FINAL DE backend/app/api/simulation.py
# ============================================================

# --- Endpoint 1: Preview de agentes ---

"""
@simulation_bp.route('/preview-agents', methods=['POST'])
def preview_agents():
    '''
    Gera preview dos agentes para o usuário revisar antes de iniciar.
    Usa o mesmo pipeline de generate-profiles, mas retorna para aprovação.
    
    JSON:
        {
            "graph_id": "mirofish_xxxx",
            "entity_types": null,  // null = todos
            "num_agents": 20
        }
    
    Retorna:
        {
            "success": true,
            "data": {
                "agents": [
                    {
                        "id": "agent_001",
                        "name": "Maria da Silva",
                        "username": "maria_silva",
                        "bio": "Dona de casa, 52 anos...",
                        "persona": "Texto completo da persona...",
                        "age": 52,
                        "gender": "female",
                        "mbti": "ISFJ",
                        "profession": "Dona de casa",
                        "source_entity_type": "Consumer",
                        "tipo": "Neutro",
                        "_custom": false
                    }
                ],
                "count": 20,
                "distribution": {"Apoiador": 6, "Neutro": 7, "Resistente": 4, "Cauteloso": 3}
            }
        }
    '''
    try:
        data = request.get_json() or {}
        graph_id = data.get('graph_id')
        
        if not graph_id:
            return jsonify({"success": False, "error": "graph_id obrigatório"}), 400
        
        entity_types = data.get('entity_types')
        num_agents = data.get('num_agents', 20)
        
        # Ler entidades do grafo
        reader = ZepEntityReader()
        filtered = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=entity_types,
            enrich_with_edges=True
        )
        
        if filtered.filtered_count == 0:
            return jsonify({"success": False, "error": "Nenhuma entidade encontrada no grafo"}), 400
        
        # Limitar ao número solicitado
        entities = filtered.entities[:num_agents]
        
        # Gerar perfis
        generator = OasisProfileGenerator(graph_id=graph_id)
        profiles = generator.generate_profiles_from_entities(
            entities=entities,
            use_llm=True,
            graph_id=graph_id
        )
        
        # Formatar para preview
        agents = []
        for i, p in enumerate(profiles):
            agent = p.to_dict()
            agent['id'] = f'agent_{i:03d}'
            agent['_custom'] = False
            agents.append(agent)
        
        # Calcular distribuição
        distribution = {}
        for a in agents:
            tipo = a.get('source_entity_type', 'Outro')
            distribution[tipo] = distribution.get(tipo, 0) + 1
        
        return jsonify({
            "success": True,
            "data": {
                "agents": agents,
                "count": len(agents),
                "distribution": distribution
            }
        })
        
    except Exception as e:
        logger.error(f"Preview agents falhou: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
"""


# --- Endpoint 2: Gerar agente customizado ---

"""
@simulation_bp.route('/custom-agent', methods=['POST'])
def create_custom_agent():
    '''
    Gera um perfil completo a partir de uma descrição em texto livre.
    
    JSON:
        {
            "description": "Marcia, 35 anos, compra tenis pela Netshoes, nunca entra em loja fisica",
            "simulation_requirement": "abertura de loja de calçados em Pádua",
            "graph_id": "mirofish_xxxx"
        }
    
    Retorna:
        {
            "success": true,
            "data": {
                "id": "custom_001",
                "name": "Márcia Oliveira",
                "bio": "Compradora online, 35 anos...",
                "persona": "...",
                "age": 35,
                "profession": "Analista de Marketing",
                "source_entity_type": "Consumer",
                "_custom": true
            }
        }
    '''
    try:
        data = request.get_json() or {}
        description = data.get('description', '')
        
        if not description or len(description) < 5:
            return jsonify({"success": False, "error": "Descrição muito curta"}), 400
        
        simulation_requirement = data.get('simulation_requirement', '')
        
        # Usar LLM para gerar perfil completo
        from ..utils.llm_client import LLMClient
        from ..config import Config
        
        llm = LLMClient()
        
        prompt = f"""Gere um perfil de agente para simulação de opinião pública em redes sociais.

DESCRIÇÃO DO USUÁRIO: {description}
CONTEXTO DA SIMULAÇÃO: {simulation_requirement}

Gere um JSON com:
- "name": Nome completo fictício brasileiro
- "username": Username para redes sociais (snake_case)
- "bio": Biografia curta (máx 200 chars) em PT-BR
- "persona": Descrição detalhada (máx 1500 chars) incluindo personalidade, comportamento, motivações
- "age": Idade (número inteiro)
- "gender": "male" ou "female"
- "mbti": Tipo MBTI
- "profession": Profissão em PT-BR
- "interested_topics": Lista de 3-5 tópicos de interesse
- "source_entity_type": Tipo mais próximo (Consumer, Influencer, Competitor, Professional, Person)

Retorne APENAS JSON válido. Tudo em PT-BR exceto gender e mbti."""

        result = llm.chat_json(
            messages=[
                {"role": "system", "content": "Você gera perfis de agentes para simulação. Retorne apenas JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Adicionar marcadores
        result['id'] = f'custom_{int(time.time())}'
        result['_custom'] = True
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Custom agent falhou: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
"""


# --- Endpoint 3: Aprovar lista de agentes ---

"""
@simulation_bp.route('/approve-agents', methods=['POST'])
def approve_agents():
    '''
    Salva a lista aprovada de agentes para uso na simulação.
    Chamado após o usuário revisar o preview.
    
    JSON:
        {
            "simulation_id": "sim_xxxx",
            "agents": [...]  // Lista completa de agentes aprovados
        }
    
    Salva em: data/simulations/{sim_id}/approved_profiles.json
    '''
    try:
        data = request.get_json() or {}
        simulation_id = data.get('simulation_id')
        agents = data.get('agents', [])
        
        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id obrigatório"}), 400
        
        if not agents:
            return jsonify({"success": False, "error": "Lista de agentes vazia"}), 400
        
        # Salvar como reddit_profiles.json (formato que a simulação espera)
        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        
        profiles_path = os.path.join(sim_dir, "reddit_profiles.json")
        
        # Converter para formato Reddit se necessário
        reddit_profiles = []
        for agent in agents:
            profile = {
                "username": agent.get("username", agent.get("name", "agent").replace(" ", "_").lower()),
                "name": agent.get("name", ""),
                "bio": agent.get("bio", ""),
                "persona": agent.get("persona", agent.get("bio", "")),
                "age": agent.get("age", 30),
                "gender": agent.get("gender", "female"),
                "mbti": agent.get("mbti", "INFP"),
                "country": agent.get("country", "Brasil"),
                "profession": agent.get("profession", ""),
                "interested_topics": agent.get("interested_topics", []),
            }
            reddit_profiles.append(profile)
        
        with open(profiles_path, 'w', encoding='utf-8') as f:
            json.dump(reddit_profiles, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Approved {len(reddit_profiles)} agents for simulation {simulation_id}")
        
        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "agents_count": len(reddit_profiles),
                "profiles_path": profiles_path
            }
        })
        
    except Exception as e:
        logger.error(f"Approve agents falhou: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
"""

# ============================================================
# NOTA DE INTEGRAÇÃO
# ============================================================
# 
# Para ativar estes endpoints:
# 1. Copiar o código dos 3 endpoints (sem as aspas triplas)
#    para o final de backend/app/api/simulation.py
# 2. Importar time no topo do arquivo: import time
# 
# Para conectar ao frontend:
# 1. Copiar AgentPreview.vue para frontend/src/components/
# 2. No SimulationView.vue, adicionar tela 'preview' entre
#    'agents' e 'pipeline'
# 3. Após gerar agentes, mostrar preview com AgentPreview
# 4. No confirmarAgentes(), chamar preview-agents e mostrar
# 
# ============================================================
