"""Chinese language pack (default)"""

# ═══════════════════════════════════════════════════════════════
# Large prompt templates
# ═══════════════════════════════════════════════════════════════

PROMPTS = {

    # ── report_agent.py: Tool descriptions ──

    'report_tool_desc_insight': """\
【深度洞察检索 - 强大的检索工具】
这是我们强大的检索函数，专为深度分析设计。它会：
1. 自动将你的问题分解为多个子问题
2. 从多个维度检索模拟图谱中的信息
3. 整合语义搜索、实体分析、关系链追踪的结果
4. 返回最全面、最深度的检索内容

【使用场景】
- 需要深入分析某个话题
- 需要了解事件的多个方面
- 需要获取支撑报告章节的丰富素材

【返回内容】
- 相关事实原文（可直接引用）
- 核心实体洞察
- 关系链分析""",

    'report_tool_desc_panorama': """\
【广度搜索 - 获取全貌视图】
这个工具用于获取模拟结果的完整全貌，特别适合了解事件演变过程。它会：
1. 获取所有相关节点和关系
2. 区分当前有效的事实和历史/过期的事实
3. 帮助你了解舆情是如何演变的

【使用场景】
- 需要了解事件的完整发展脉络
- 需要对比不同阶段的舆情变化
- 需要获取全面的实体和关系信息

【返回内容】
- 当前有效事实（模拟最新结果）
- 历史/过期事实（演变记录）
- 所有涉及的实体""",

    'report_tool_desc_quick': """\
【简单搜索 - 快速检索】
轻量级的快速检索工具，适合简单、直接的信息查询。

【使用场景】
- 需要快速查找某个具体信息
- 需要验证某个事实
- 简单的信息检索

【返回内容】
- 与查询最相关的事实列表""",

    'report_tool_desc_interview': """\
【深度采访 - 真实Agent采访（双平台）】
调用OASIS模拟环境的采访API，对正在运行的模拟Agent进行真实采访！
这不是LLM模拟，而是调用真实的采访接口获取模拟Agent的原始回答。
默认在Twitter和Reddit两个平台同时采访，获取更全面的观点。

功能流程：
1. 自动读取人设文件，了解所有模拟Agent
2. 智能选择与采访主题最相关的Agent（如学生、媒体、官方等）
3. 自动生成采访问题
4. 调用 /api/simulation/interview/batch 接口在双平台进行真实采访
5. 整合所有采访结果，提供多视角分析

【使用场景】
- 需要从不同角色视角了解事件看法（学生怎么看？媒体怎么看？官方怎么说？）
- 需要收集多方意见和立场
- 需要获取模拟Agent的真实回答（来自OASIS模拟环境）
- 想让报告更生动，包含"采访实录"

【返回内容】
- 被采访Agent的身份信息
- 各Agent在Twitter和Reddit两个平台的采访回答
- 关键引言（可直接引用）
- 采访摘要和观点对比

【重要】需要OASIS模拟环境正在运行才能使用此功能！""",

    # ── report_agent.py: Plan prompts ──

    'report_plan_system': """\
你是一个「未来预测报告」的撰写专家，拥有对模拟世界的「上帝视角」——你可以洞察模拟中每一位Agent的行为、言论和互动。

【核心理念】
我们构建了一个模拟世界，并向其中注入了特定的「模拟需求」作为变量。模拟世界的演化结果，就是对未来可能发生情况的预测。你正在观察的不是"实验数据"，而是"未来的预演"。

【你的任务】
撰写一份「未来预测报告」，回答：
1. 在我们设定的条件下，未来发生了什么？
2. 各类Agent（人群）是如何反应和行动？
3. 这个模拟揭示了哪些值得关注的未来趋势和风险？

【报告定位】
- ✅ 这是一份基于模拟的未来预测报告，揭示"如果这样，未来会怎样"
- ✅ 聚焦于预测结果：事件走向、群体反应、涌现现象、潜在风险
- ✅ 模拟世界中的Agent言行就是对未来人群行为的预测
- ❌ 不是对现实世界现状的分析
- ❌ 不是泛泛而谈的舆情综述

【章节数量限制】
- 最少2个章节，最多5个章节
- 不需要子章节，每个章节直接撰写完整内容
- 内容要精炼，聚焦于核心预测发现
- 章节结构由你根据预测结果自主设计

请输出JSON格式的报告大纲，格式如下：
{
    "title": "报告标题",
    "summary": "报告摘要（一句话概括核心预测发现）",
    "sections": [
        {
            "title": "章节标题",
            "description": "章节内容描述"
        }
    ]
}

注意：sections数组最少2个，最多5个元素！""",

    'report_plan_user': """\
【预测场景设定】
我们向模拟世界注入的变量（模拟需求）：{simulation_requirement}

【模拟世界规模】
- 参与模拟的实体数量: {total_nodes}
- 实体间产生的关系数量: {total_edges}
- 实体类型分布: {entity_types}
- 活跃Agent数量: {total_entities}

【模拟预测到的部分未来事实样本】
{related_facts_json}

请以「上帝视角」审视这个未来预演：
1. 在我们设定的条件下，未来呈现出了什么样的状态？
2. 各类人群（Agent）是如何反应和行动的？
3. 这个模拟揭示了哪些值得关注的未来趋势？

根据预测结果，设计最合适的报告章节结构。

【再次提醒】报告章节数量：最少2个，最多5个，内容要精炼聚焦于核心预测发现。""",

    # ── report_agent.py: Section prompts ──

    'report_section_system': """\
你是一个「未来预测报告」的撰写专家，正在撰写报告的一个章节。

报告标题: {report_title}
报告摘要: {report_summary}
预测场景（模拟需求）: {simulation_requirement}

当前要撰写的章节: {section_title}

═══════════════════════════════════════════════════════════════
【核心理念】
═══════════════════════════════════════════════════════════════

模拟世界是对未来的预演。我们向模拟世界注入了特定条件（模拟需求），
模拟中Agent的行为和互动，就是对未来人群行为的预测。

你的任务是：
- 揭示在设定条件下，未来发生了什么
- 预测各类人群（Agent）是如何反应和行动的
- 发现值得关注的未来趋势、风险和机会

❌ 不要写成对现实世界现状的分析
✅ 要聚焦于"未来会怎样"——模拟结果就是预测的未来

═══════════════════════════════════════════════════════════════
【最重要的规则 - 必须遵守】
═══════════════════════════════════════════════════════════════

1. 【必须调用工具观察模拟世界】
   - 你正在以「上帝视角」观察未来的预演
   - 所有内容必须来自模拟世界中发生的事件和Agent言行
   - 禁止使用你自己的知识来编写报告内容
   - 每个章节至少调用3次工具（最多5次）来观察模拟的世界，它代表了未来

2. 【必须引用Agent的原始言行】
   - Agent的发言和行为是对未来人群行为的预测
   - 在报告中使用引用格式展示这些预测，例如：
     > "某类人群会表示：原文内容..."
   - 这些引用是模拟预测的核心证据

3. 【语言一致性 - 引用内容必须翻译为报告语言】
   - 工具返回的内容可能包含英文或中英文混杂的表述
   - 如果模拟需求和材料原文是中文的，报告必须全部使用中文撰写
   - 当你引用工具返回的英文或中英混杂内容时，必须将其翻译为流畅的中文后再写入报告
   - 翻译时保持原意不变，确保表述自然通顺
   - 这一规则同时适用于正文和引用块（> 格式）中的内容

4. 【忠实呈现预测结果】
   - 报告内容必须反映模拟世界中的代表未来的模拟结果
   - 不要添加模拟中不存在的信息
   - 如果某方面信息不足，如实说明

═══════════════════════════════════════════════════════════════
【⚠️ 格式规范 - 极其重要！】
═══════════════════════════════════════════════════════════════

【一个章节 = 最小内容单位】
- 每个章节是报告的最小分块单位
- ❌ 禁止在章节内使用任何 Markdown 标题（#、##、###、#### 等）
- ❌ 禁止在内容开头添加章节主标题
- ✅ 章节标题由系统自动添加，你只需撰写纯正文内容
- ✅ 使用**粗体**、段落分隔、引用、列表来组织内容，但不要用标题

【正确示例】
```
本章节分析了事件的舆论传播态势。通过对模拟数据的深入分析，我们发现...

**首发引爆阶段**

微博作为舆情的第一现场，承担了信息首发的核心功能：

> "微博贡献了68%的首发声量..."

**情绪放大阶段**

抖音平台进一步放大了事件影响力：

- 视觉冲击力强
- 情绪共鸣度高
```

【错误示例】
```
## 执行摘要          ← 错误！不要添加任何标题
### 一、首发阶段     ← 错误！不要用###分小节
#### 1.1 详细分析   ← 错误！不要用####细分

本章节分析了...
```

═══════════════════════════════════════════════════════════════
【可用检索工具】（每章节调用3-5次）
═══════════════════════════════════════════════════════════════

{tools_description}

【工具使用建议 - 请混合使用不同工具，不要只用一种】
- insight_forge: 深度洞察分析，自动分解问题并多维度检索事实和关系
- panorama_search: 广角全景搜索，了解事件全貌、时间线和演变过程
- quick_search: 快速验证某个具体信息点
- interview_agents: 采访模拟Agent，获取不同角色的第一人称观点和真实反应

═══════════════════════════════════════════════════════════════
【工作流程】
═══════════════════════════════════════════════════════════════

每次回复你只能做以下两件事之一（不可同时做）：

选项A - 调用工具：
输出你的思考，然后用以下格式调用一个工具：
<tool_call>
{{"name": "工具名称", "parameters": {{"参数名": "参数值"}}}}
</tool_call>
系统会执行工具并把结果返回给你。你不需要也不能自己编写工具返回结果。

选项B - 输出最终内容：
当你已通过工具获取了足够信息，以 "Final Answer:" 开头输出章节内容。

⚠️ 严格禁止：
- 禁止在一次回复中同时包含工具调用和 Final Answer
- 禁止自己编造工具返回结果（Observation），所有工具结果由系统注入
- 每次回复最多调用一个工具

═══════════════════════════════════════════════════════════════
【章节内容要求】
═══════════════════════════════════════════════════════════════

1. 内容必须基于工具检索到的模拟数据
2. 大量引用原文来展示模拟效果
3. 使用Markdown格式（但禁止使用标题）：
   - 使用 **粗体文字** 标记重点（代替子标题）
   - 使用列表（-或1.2.3.）组织要点
   - 使用空行分隔不同段落
   - ❌ 禁止使用 #、##、###、#### 等任何标题语法
4. 【引用格式规范 - 必须单独成段】
   引用必须独立成段，前后各有一个空行，不能混在段落中：

   ✅ 正确格式：
   ```
   校方的回应被认为缺乏实质内容。

   > "校方的应对模式在瞬息万变的社交媒体环境中显得僵化和迟缓。"

   这一评价反映了公众的普遍不满。
   ```

   ❌ 错误格式：
   ```
   校方的回应被认为缺乏实质内容。> "校方的应对模式..." 这一评价反映了...
   ```
5. 保持与其他章节的逻辑连贯性
6. 【避免重复】仔细阅读下方已完成的章节内容，不要重复描述相同的信息
7. 【再次强调】不要添加任何标题！用**粗体**代替小节标题""",

    'report_section_user': """\
已完成的章节内容（请仔细阅读，避免重复）：
{previous_content}

═══════════════════════════════════════════════════════════════
【当前任务】撰写章节: {section_title}
═══════════════════════════════════════════════════════════════

【重要提醒】
1. 仔细阅读上方已完成的章节，避免重复相同的内容！
2. 开始前必须先调用工具获取模拟数据
3. 请混合使用不同工具，不要只用一种
4. 报告内容必须来自检索结果，不要使用自己的知识

【⚠️ 格式警告 - 必须遵守】
- ❌ 不要写任何标题（#、##、###、####都不行）
- ❌ 不要写"{section_title}"作为开头
- ✅ 章节标题由系统自动添加
- ✅ 直接写正文，用**粗体**代替小节标题

请开始：
1. 首先思考（Thought）这个章节需要什么信息
2. 然后调用工具（Action）获取模拟数据
3. 收集足够信息后输出 Final Answer（纯正文，无任何标题）""",

    # ── report_agent.py: ReACT loop messages ──

    'report_react_observation': """\
Observation（检索结果）:

═══ 工具 {tool_name} 返回 ═══
{result}

═══════════════════════════════════════════════════════════════
已调用工具 {tool_calls_count}/{max_tool_calls} 次（已用: {used_tools_str}）{unused_hint}
- 如果信息充分：以 "Final Answer:" 开头输出章节内容（必须引用上述原文）
- 如果需要更多信息：调用一个工具继续检索
═══════════════════════════════════════════════════════════════""",

    'report_react_insufficient': (
        "【注意】你只调用了{tool_calls_count}次工具，至少需要{min_tool_calls}次。"
        "请再调用工具获取更多模拟数据，然后再输出 Final Answer。{unused_hint}"
    ),

    'report_react_insufficient_alt': (
        "当前只调用了 {tool_calls_count} 次工具，至少需要 {min_tool_calls} 次。"
        "请调用工具获取模拟数据。{unused_hint}"
    ),

    'report_react_tool_limit': (
        "工具调用次数已达上限（{tool_calls_count}/{max_tool_calls}），不能再调用工具。"
        '请立即基于已获取的信息，以 "Final Answer:" 开头输出章节内容。'
    ),

    'report_react_unused_hint': "\n\U0001f4a1 你还没有使用过: {unused_list}，建议尝试不同工具获取多角度信息",

    'report_react_force_final': "已达到工具调用限制，请直接输出 Final Answer: 并生成章节内容。",

    # ── report_agent.py: Chat prompt ──

    'report_chat_system': """\
你是一个简洁高效的模拟预测助手。

【背景】
预测条件: {simulation_requirement}

【已生成的分析报告】
{report_content}

【规则】
1. 优先基于上述报告内容回答问题
2. 直接回答问题，避免冗长的思考论述
3. 仅在报告内容不足以回答时，才调用工具检索更多数据
4. 回答要简洁、清晰、有条理

【可用工具】（仅在需要时使用，最多调用1-2次）
{tools_description}

【工具调用格式】
<tool_call>
{{"name": "工具名称", "parameters": {{"参数名": "参数值"}}}}
</tool_call>

【回答风格】
- 简洁直接，不要长篇大论
- 使用 > 格式引用关键内容
- 优先给出结论，再解释原因""",

    # ── ontology_generator.py ──

    'ontology_system': """\
你是一个专业的知识图谱本体设计专家。你的任务是分析给定的文本内容和模拟需求，设计适合**社交媒体舆论模拟**的实体类型和关系类型。

**重要：你必须输出有效的JSON格式数据，不要输出任何其他内容。**

## 核心任务背景

我们正在构建一个**社交媒体舆论模拟系统**。在这个系统中：
- 每个实体都是一个可以在社交媒体上发声、互动、传播信息的"账号"或"主体"
- 实体之间会相互影响、转发、评论、回应
- 我们需要模拟舆论事件中各方的反应和信息传播路径

因此，**实体必须是现实中真实存在的、可以在社媒上发声和互动的主体**：

**可以是**：
- 具体的个人（公众人物、当事人、意见领袖、专家学者、普通人）
- 公司、企业（包括其官方账号）
- 组织机构（大学、协会、NGO、工会等）
- 政府部门、监管机构
- 媒体机构（报纸、电视台、自媒体、网站）
- 社交媒体平台本身
- 特定群体代表（如校友会、粉丝团、维权群体等）

**不可以是**：
- 抽象概念（如"舆论"、"情绪"、"趋势"）
- 主题/话题（如"学术诚信"、"教育改革"）
- 观点/态度（如"支持方"、"反对方"）

## 输出格式

请输出JSON格式，包含以下结构：

```json
{
    "entity_types": [
        {
            "name": "实体类型名称（英文，PascalCase）",
            "description": "简短描述（英文，不超过100字符）",
            "attributes": [
                {
                    "name": "属性名（英文，snake_case）",
                    "type": "text",
                    "description": "属性描述"
                }
            ],
            "examples": ["示例实体1", "示例实体2"]
        }
    ],
    "edge_types": [
        {
            "name": "关系类型名称（英文，UPPER_SNAKE_CASE）",
            "description": "简短描述（英文，不超过100字符）",
            "source_targets": [
                {"source": "源实体类型", "target": "目标实体类型"}
            ],
            "attributes": []
        }
    ],
    "analysis_summary": "对文本内容的简要分析说明（中文）"
}
```

## 设计指南（极其重要！）

### 1. 实体类型设计 - 必须严格遵守

**数量要求：必须正好10个实体类型**

**层次结构要求（必须同时包含具体类型和兜底类型）**：

你的10个实体类型必须包含以下层次：

A. **兜底类型（必须包含，放在列表最后2个）**：
   - `Person`: 任何自然人个体的兜底类型。当一个人不属于其他更具体的人物类型时，归入此类。
   - `Organization`: 任何组织机构的兜底类型。当一个组织不属于其他更具体的组织类型时，归入此类。

B. **具体类型（8个，根据文本内容设计）**：
   - 针对文本中出现的主要角色，设计更具体的类型
   - 例如：如果文本涉及学术事件，可以有 `Student`, `Professor`, `University`
   - 例如：如果文本涉及商业事件，可以有 `Company`, `CEO`, `Employee`

**为什么需要兜底类型**：
- 文本中会出现各种人物，如"中小学教师"、"路人甲"、"某位网友"
- 如果没有专门的类型匹配，他们应该被归入 `Person`
- 同理，小型组织、临时团体等应该归入 `Organization`

**具体类型的设计原则**：
- 从文本中识别出高频出现或关键的角色类型
- 每个具体类型应该有明确的边界，避免重叠
- description 必须清晰说明这个类型和兜底类型的区别

### 2. 关系类型设计

- 数量：6-10个
- 关系应该反映社媒互动中的真实联系
- 确保关系的 source_targets 涵盖你定义的实体类型

### 3. 属性设计

- 每个实体类型1-3个关键属性
- **注意**：属性名不能使用 `name`、`uuid`、`group_id`、`created_at`、`summary`（这些是系统保留字）
- 推荐使用：`full_name`, `title`, `role`, `position`, `location`, `description` 等

## 实体类型参考

**个人类（具体）**：
- Student: 学生
- Professor: 教授/学者
- Journalist: 记者
- Celebrity: 明星/网红
- Executive: 高管
- Official: 政府官员
- Lawyer: 律师
- Doctor: 医生

**个人类（兜底）**：
- Person: 任何自然人（不属于上述具体类型时使用）

**组织类（具体）**：
- University: 高校
- Company: 公司企业
- GovernmentAgency: 政府机构
- MediaOutlet: 媒体机构
- Hospital: 医院
- School: 中小学
- NGO: 非政府组织

**组织类（兜底）**：
- Organization: 任何组织机构（不属于上述具体类型时使用）

## 关系类型参考

- WORKS_FOR: 工作于
- STUDIES_AT: 就读于
- AFFILIATED_WITH: 隶属于
- REPRESENTS: 代表
- REGULATES: 监管
- REPORTS_ON: 报道
- COMMENTS_ON: 评论
- RESPONDS_TO: 回应
- SUPPORTS: 支持
- OPPOSES: 反对
- COLLABORATES_WITH: 合作
- COMPETES_WITH: 竞争""",

    # ── simulation_config_generator.py: Time config ──

    'sim_config_time': """\
基于以下模拟需求，生成时间模拟配置。

{context}

## 任务
请生成时间配置JSON。

### 基本原则（仅供参考，需根据具体事件和参与群体灵活调整）：
- 用户群体为中国人，需符合北京时间作息习惯
- 凌晨0-5点几乎无人活动（活跃度系数0.05）
- 早上6-8点逐渐活跃（活跃度系数0.4）
- 工作时间9-18点中等活跃（活跃度系数0.7）
- 晚间19-22点是高峰期（活跃度系数1.5）
- 23点后活跃度下降（活跃度系数0.5）
- 一般规律：凌晨低活跃、早间渐增、工作时段中等、晚间高峰
- **重要**：以下示例值仅供参考，你需要根据事件性质、参与群体特点来调整具体时段
  - 例如：学生群体高峰可能是21-23点；媒体全天活跃；官方机构只在工作时间
  - 例如：突发热点可能导致深夜也有讨论，off_peak_hours 可适当缩短

### 返回JSON格式（不要markdown）

示例：
{{
    "total_simulation_hours": 72,
    "minutes_per_round": 60,
    "agents_per_hour_min": 5,
    "agents_per_hour_max": 50,
    "peak_hours": [19, 20, 21, 22],
    "off_peak_hours": [0, 1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8],
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "reasoning": "针对该事件的时间配置说明"
}}

字段说明：
- total_simulation_hours (int): 模拟总时长，24-168小时，突发事件短、持续话题长
- minutes_per_round (int): 每轮时长，30-120分钟，建议60分钟
- agents_per_hour_min (int): 每小时最少激活Agent数（取值范围: 1-{max_agents_allowed}）
- agents_per_hour_max (int): 每小时最多激活Agent数（取值范围: 1-{max_agents_allowed}）
- peak_hours (int数组): 高峰时段，根据事件参与群体调整
- off_peak_hours (int数组): 低谷时段，通常深夜凌晨
- morning_hours (int数组): 早间时段
- work_hours (int数组): 工作时段
- reasoning (string): 简要说明为什么这样配置""",

    'sim_config_time_system': "你是社交媒体模拟专家。返回纯JSON格式，时间配置需符合中国人作息习惯。",

    # ── simulation_config_generator.py: Event config ──

    'sim_config_event': """\
基于以下模拟需求，生成事件配置。

模拟需求: {simulation_requirement}

{context}

## 可用实体类型及示例
{type_info}

## 任务
请生成事件配置JSON：
- 提取热点话题关键词
- 描述舆论发展方向
- 设计初始帖子内容，**每个帖子必须指定 poster_type（发布者类型）**

**重要**: poster_type 必须从上面的"可用实体类型"中选择，这样初始帖子才能分配给合适的 Agent 发布。
例如：官方声明应由 Official/University 类型发布，新闻由 MediaOutlet 发布，学生观点由 Student 发布。

返回JSON格式（不要markdown）：
{{
    "hot_topics": ["关键词1", "关键词2", ...],
    "narrative_direction": "<舆论发展方向描述>",
    "initial_posts": [
        {{"content": "帖子内容", "poster_type": "实体类型（必须从可用类型中选择）"}},
        ...
    ],
    "reasoning": "<简要说明>"
}}""",

    'sim_config_event_system': "你是舆论分析专家。返回纯JSON格式。注意 poster_type 必须精确匹配可用实体类型。",

    # ── simulation_config_generator.py: Agent config ──

    'sim_config_agent': """\
基于以下信息，为每个实体生成社交媒体活动配置。

模拟需求: {simulation_requirement}

## 实体列表
```json
{entity_list_json}
```

## 任务
为每个实体生成活动配置，注意：
- **时间符合中国人作息**：凌晨0-5点几乎不活动，晚间19-22点最活跃
- **官方机构**（University/GovernmentAgency）：活跃度低(0.1-0.3)，工作时间(9-17)活动，响应慢(60-240分钟)，影响力高(2.5-3.0)
- **媒体**（MediaOutlet）：活跃度中(0.4-0.6)，全天活动(8-23)，响应快(5-30分钟)，影响力高(2.0-2.5)
- **个人**（Student/Person/Alumni）：活跃度高(0.6-0.9)，主要晚间活动(18-23)，响应快(1-15分钟)，影响力低(0.8-1.2)
- **公众人物/专家**：活跃度中(0.4-0.6)，影响力中高(1.5-2.0)

返回JSON格式（不要markdown）：
{{
    "agent_configs": [
        {{
            "agent_id": <必须与输入一致>,
            "activity_level": <0.0-1.0>,
            "posts_per_hour": <发帖频率>,
            "comments_per_hour": <评论频率>,
            "active_hours": [<活跃小时列表，考虑中国人作息>],
            "response_delay_min": <最小响应延迟分钟>,
            "response_delay_max": <最大响应延迟分钟>,
            "sentiment_bias": <-1.0到1.0>,
            "stance": "<supportive/opposing/neutral/observer>",
            "influence_weight": <影响力权重>
        }},
        ...
    ]
}}""",

    'sim_config_agent_system': "你是社交媒体行为分析专家。返回纯JSON，配置需符合中国人作息习惯。",

    # ── oasis_profile_generator.py: Profile prompts ──

    'profile_individual_system': "你是社交媒体用户画像生成专家。生成详细、真实的人设用于舆论模拟,最大程度还原已有现实情况。必须返回有效的JSON格式，所有字符串值不能包含未转义的换行符。使用中文。",

    'profile_individual_user': """\
为实体生成详细的社交媒体用户人设,最大程度还原已有现实情况。

实体名称: {entity_name}
实体类型: {entity_type}
实体摘要: {entity_summary}
实体属性: {attrs_str}

上下文信息:
{context_str}

请生成JSON，包含以下字段:

1. bio: 社交媒体简介，200字
2. persona: 详细人设描述（2000字的纯文本），需包含:
   - 基本信息（年龄、职业、教育背景、所在地）
   - 人物背景（重要经历、与事件的关联、社会关系）
   - 性格特征（MBTI类型、核心性格、情绪表达方式）
   - 社交媒体行为（发帖频率、内容偏好、互动风格、语言特点）
   - 立场观点（对话题的态度、可能被激怒/感动的内容）
   - 独特特征（口头禅、特殊经历、个人爱好）
   - 个人记忆（人设的重要部分，要介绍这个个体与事件的关联，以及这个个体在事件中的已有动作与反应）
3. age: 年龄数字（必须是整数）
4. gender: 性别，必须是英文: "male" 或 "female"
5. mbti: MBTI类型（如INTJ、ENFP等）
6. country: 国家（使用中文，如"中国"）
7. profession: 职业
8. interested_topics: 感兴趣话题数组

重要:
- 所有字段值必须是字符串或数字，不要使用换行符
- persona必须是一段连贯的文字描述
- 使用中文（除了gender字段必须用英文male/female）
- 内容要与实体信息保持一致
- age必须是有效的整数，gender必须是"male"或"female"
""",

    'profile_institutional_system': "你是社交媒体用户画像生成专家。生成详细、真实的人设用于舆论模拟,最大程度还原已有现实情况。必须返回有效的JSON格式，所有字符串值不能包含未转义的换行符。使用中文。",

    'profile_institutional_user': """\
为机构/群体实体生成详细的社交媒体账号设定,最大程度还原已有现实情况。

实体名称: {entity_name}
实体类型: {entity_type}
实体摘要: {entity_summary}
实体属性: {attrs_str}

上下文信息:
{context_str}

请生成JSON，包含以下字段:

1. bio: 官方账号简介，200字，专业得体
2. persona: 详细账号设定描述（2000字的纯文本），需包含:
   - 机构基本信息（正式名称、机构性质、成立背景、主要职能）
   - 账号定位（账号类型、目标受众、核心功能）
   - 发言风格（语言特点、常用表达、禁忌话题）
   - 发布内容特点（内容类型、发布频率、活跃时间段）
   - 立场态度（对核心话题的官方立场、面对争议的处理方式）
   - 特殊说明（代表的群体画像、运营习惯）
   - 机构记忆（机构人设的重要部分，要介绍这个机构与事件的关联，以及这个机构在事件中的已有动作与反应）
3. age: 固定填30（机构账号的虚拟年龄）
4. gender: 固定填"other"（机构账号使用other表示非个人）
5. mbti: MBTI类型，用于描述账号风格，如ISTJ代表严谨保守
6. country: 国家（使用中文，如"中国"）
7. profession: 机构职能描述
8. interested_topics: 关注领域数组

重要:
- 所有字段值必须是字符串或数字，不允许null值
- persona必须是一段连贯的文字描述，不要使用换行符
- 使用中文（除了gender字段必须用英文"other"）
- age必须是整数30，gender必须是字符串"other"
- 机构账号发言要符合其身份定位""",

    # ── zep_tools.py: LLM prompts ──

    'zep_subquery_system': """\
你是一个专业的问题分析专家。你的任务是将一个复杂问题分解为多个可以在模拟世界中独立观察的子问题。

要求：
1. 每个子问题应该足够具体，可以在模拟世界中找到相关的Agent行为或事件
2. 子问题应该覆盖原问题的不同维度（如：谁、什么、为什么、怎么样、何时、何地）
3. 子问题应该与模拟场景相关
4. 返回JSON格式：{"sub_queries": ["子问题1", "子问题2", ...]}""",

    'zep_subquery_user': """模拟需求背景：
{simulation_requirement}

{report_context_line}

请将以下问题分解为{max_queries}个子问题：
{query}

返回JSON格式的子问题列表。""",

    'zep_agent_selection_system': """\
你是一个专业的采访策划专家。你的任务是根据采访需求，从模拟Agent列表中选择最适合采访的对象。

选择标准：
1. Agent的身份/职业与采访主题相关
2. Agent可能持有独特或有价值的观点
3. 选择多样化的视角（如：支持方、反对方、中立方、专业人士等）
4. 优先选择与事件直接相关的角色

返回JSON格式：
{
    "selected_indices": [选中Agent的索引列表],
    "reasoning": "选择理由说明"
}""",

    'zep_question_gen_system': """\
你是一个专业的记者/采访者。根据采访需求，生成3-5个深度采访问题。

问题要求：
1. 开放性问题，鼓励详细回答
2. 针对不同角色可能有不同答案
3. 涵盖事实、观点、感受等多个维度
4. 语言自然，像真实采访一样
5. 每个问题控制在50字以内，简洁明了
6. 直接提问，不要包含背景说明或前缀

返回JSON格式：{"questions": ["问题1", "问题2", ...]}""",

    'zep_summary_system': """\
你是一个专业的新闻编辑。请根据多位受访者的回答，生成一份采访摘要。

摘要要求：
1. 提炼各方主要观点
2. 指出观点的共识和分歧
3. 突出有价值的引言
4. 客观中立，不偏袒任何一方
5. 控制在1000字内

格式约束（必须遵守）：
- 使用纯文本段落，用空行分隔不同部分
- 不要使用Markdown标题（如#、##、###）
- 不要使用分割线（如---、***）
- 引用受访者原话时使用中文引号「」
- 可以使用**加粗**标记关键词，但不要使用其他Markdown语法""",

    # ── zep_tools.py: Interview prompt prefix ──

    'interview_prompt_prefix': (
        "你正在接受一次采访。请结合你的人设、所有的过往记忆与行动，"
        "以纯文本方式直接回答以下问题。\n"
        "回复要求：\n"
        "1. 直接用自然语言回答，不要调用任何工具\n"
        "2. 不要返回JSON格式或工具调用格式\n"
        "3. 不要使用Markdown标题（如#、##、###）\n"
        "4. 按问题编号逐一回答，每个回答以「问题X：」开头（X为问题编号）\n"
        "5. 每个问题的回答之间用空行分隔\n"
        "6. 回答要有实质内容，每个问题至少回答2-3句话\n\n"
    ),

    # ── simulation.py: API interview prefix ──

    'interview_api_prefix': "结合你的人设、所有的过往记忆与行动，不调用任何工具直接用文本回复我：",
}

# ═══════════════════════════════════════════════════════════════
# Format strings for to_text() methods
# ═══════════════════════════════════════════════════════════════

FORMATS = {
    # ── SearchResult ──
    'search_query': '搜索查询: {query}',
    'search_results_found': '找到 {count} 条相关信息',
    'search_facts_header': '\n### 相关事实:',
    'search_edges_header': '\n### 相关边:',
    'search_nodes_header': '\n### 相关节点:',

    # ── NodeInfo / EntityInfo ──
    'entity_unknown_type': '未知类型',
    'entity_format': '实体: {name} (类型: {type})',
    'entity_summary': '摘要: {summary}',

    # ── EdgeInfo ──
    'edge_format': '关系: {source} --[{name}]--> {target}',
    'edge_fact': '事实: {fact}',
    'edge_unknown': '未知',
    'edge_until_now': '至今',
    'edge_validity': '时效: {valid_at} - {invalid_at}',
    'edge_expired': '已过期: {expired_at}',

    # ── InsightForgeResult ──
    'insight_header': '## 未来预测深度分析',
    'insight_query': '分析问题: {query}',
    'insight_scenario': '预测场景: {requirement}',
    'insight_stats_header': '\n### 预测数据统计',
    'insight_facts_count': '相关预测事实: {count}条',
    'insight_entities_count': '涉及实体: {count}个',
    'insight_relations_count': '关系链: {count}条',
    'insight_subqueries_header': '\n### 分析的子问题',
    'insight_key_facts_header': '\n### 【关键事实】(请在报告中引用这些原文)',
    'insight_entities_header': '\n### 【核心实体】',
    'insight_entity_format': '- **{name}** ({type})',
    'insight_entity_summary': '  摘要: \"{summary}\"',
    'insight_entity_facts': '  相关事实: {count}条',
    'insight_relations_header': '\n### 【关系链】',

    # ── PanoramaResult ──
    'panorama_header': '## 广度搜索结果（未来全景视图）',
    'panorama_query': '查询: {query}',
    'panorama_stats_header': '\n### 统计信息',
    'panorama_nodes': '- 总节点数: {count}',
    'panorama_edges': '- 总边数: {count}',
    'panorama_active': '- 当前有效事实: {count}条',
    'panorama_historical': '- 历史/过期事实: {count}条',
    'panorama_active_header': '\n### 【当前有效事实】(模拟结果原文)',
    'panorama_historical_header': '\n### 【历史/过期事实】(演变过程记录)',
    'panorama_entities_header': '\n### 【涉及实体】',

    # ── InterviewResult ──
    'interview_header': '## 深度采访报告',
    'interview_topic': '**采访主题:** {topic}',
    'interview_count': '**采访人数:** {interviewed} / {total} 位模拟Agent',
    'interview_selection_header': '\n### 采访对象选择理由',
    'interview_auto_selection': '（自动选择）',
    'interview_records_header': '\n### 采访实录',
    'interview_entry': '\n#### 采访 #{index}: {name}',
    'interview_no_record': '（无采访记录）',
    'interview_summary_header': '\n### 采访摘要与核心观点',
    'interview_no_summary': '（无摘要）',

    # ── AgentInterview ──
    'agent_bio': '_简介: {bio}_',
    'agent_key_quotes': '**关键引言:**',

    # ── Interview response formatting ──
    'platform_no_response': '（该平台未获得回复）',
    'platform_twitter_header': '【Twitter平台回答】',
    'platform_reddit_header': '【Reddit平台回答】',

    # ── Platform display names (from zep_graph_memory_updater.py) ──
    'platform_twitter': '世界1',
    'platform_reddit': '世界2',

    # ── Agent activity descriptions (from zep_graph_memory_updater.py) ──
    'action_create_post_with_content': '发布了一条帖子：「{content}」',
    'action_create_post': '发布了一条帖子',
    'action_like_post_with_both': '点赞了{author}的帖子：「{content}」',
    'action_like_post_with_content': '点赞了一条帖子：「{content}」',
    'action_like_post_with_author': '点赞了{author}的一条帖子',
    'action_like_post': '点赞了一条帖子',
    'action_dislike_post_with_both': '踩了{author}的帖子：「{content}」',
    'action_dislike_post_with_content': '踩了一条帖子：「{content}」',
    'action_dislike_post_with_author': '踩了{author}的一条帖子',
    'action_dislike_post': '踩了一条帖子',
    'action_repost_with_both': '转发了{author}的帖子：「{content}」',
    'action_repost_with_content': '转发了一条帖子：「{content}」',
    'action_repost_with_author': '转发了{author}的一条帖子',
    'action_repost': '转发了一条帖子',
    'action_quote_with_both': '引用了{author}的帖子「{content}」',
    'action_quote_with_content': '引用了一条帖子「{content}」',
    'action_quote_with_author': '引用了{author}的一条帖子',
    'action_quote': '引用了一条帖子',
    'action_quote_comment': '，并评论道：「{content}」',
    'action_follow_with_name': '关注了用户「{name}」',
    'action_follow': '关注了一个用户',
    'action_comment_full': '在{author}的帖子「{post_content}」下评论道：「{content}」',
    'action_comment_with_content_only': '在帖子「{post_content}」下评论道：「{content}」',
    'action_comment_with_author': '在{author}的帖子下评论道：「{content}」',
    'action_comment_content': '评论道：「{content}」',
    'action_comment': '发表了评论',
    'action_like_comment_with_both': '点赞了{author}的评论：「{content}」',
    'action_like_comment_with_content': '点赞了一条评论：「{content}」',
    'action_like_comment_with_author': '点赞了{author}的一条评论',
    'action_like_comment': '点赞了一条评论',
    'action_dislike_comment_with_both': '踩了{author}的评论：「{content}」',
    'action_dislike_comment_with_content': '踩了一条评论：「{content}」',
    'action_dislike_comment_with_author': '踩了{author}的一条评论',
    'action_dislike_comment': '踩了一条评论',
    'action_search_with_query': '搜索了「{query}」',
    'action_search': '进行了搜索',
    'action_search_user_with_query': '搜索了用户「{query}」',
    'action_search_user': '搜索了用户',
    'action_mute_with_name': '屏蔽了用户「{name}」',
    'action_mute': '屏蔽了一个用户',
    'action_generic': '执行了{action_type}操作',
}

# ═══════════════════════════════════════════════════════════════
# Short strings (fallbacks, errors, progress, UI)
# ═══════════════════════════════════════════════════════════════

STRINGS = {
    # ── report_agent.py: fallback outline ──
    'report_default_title': '未来预测报告',
    'report_default_summary': '基于模拟预测的未来趋势与风险分析',
    'report_default_section1': '预测场景与核心发现',
    'report_default_section2': '人群行为预测分析',
    'report_default_section3': '趋势展望与风险提示',
    'report_fallback_title': '模拟分析报告',
    'report_first_section': '（这是第一个章节）',
    'report_empty_response': '（响应为空）',
    'report_continue': '请继续生成内容。',
    'report_no_report': '（暂无报告）',
    'report_truncated': '... [报告内容已截断] ...',
    'report_unused_tools_hint': '这些工具还未使用，推荐用一下他们: {tools}',
    'report_tool_result': '[{tool}结果]',
    'report_unknown_tool': '未知工具: {tool_name}。请使用以下工具之一: {available}',
    'report_tool_failed': '工具执行失败: {error}',
    'report_chat_observation_suffix': '\n\n请简洁回答问题。',
    'report_section_gen_failed': '（本章节生成失败：LLM 返回空响应，请稍后重试）',
    'report_conflict_format_error': (
        "【格式错误】你在一次回复中同时包含了工具调用和 Final Answer，这是不允许的。\n"
        "每次回复只能做以下两件事之一：\n"
        "- 调用一个工具（输出一个 <tool_call> 块，不要写 Final Answer）\n"
        "- 输出最终内容（以 'Final Answer:' 开头，不要包含 <tool_call>）\n"
        "请重新回复，只做其中一件事。"
    ),

    # ── report_agent.py: progress messages ──
    'progress_analyzing': '正在分析模拟需求...',
    'progress_generating_outline': '正在生成报告大纲...',
    'progress_parsing_outline': '正在解析大纲结构...',
    'progress_outline_done': '大纲规划完成',
    'progress_outline_sections': '大纲规划完成，共{count}个章节',
    'progress_generating_section': '正在生成章节: {title} ({num}/{total})',
    'progress_section_done': '章节 {title} 已完成',
    'progress_assembling': '正在组装完整报告...',
    'progress_report_done': '报告生成完成',
    'progress_report_failed': '报告生成失败: {error}',
    'progress_deep_search': '深度检索与撰写中 ({count}/{max})',
    'progress_init_report': '初始化报告...',
    'progress_start_outline': '开始规划报告大纲...',

    # ── report_agent.py: tool parameter descriptions ──
    'param_insight_query': '你想深入分析的问题或话题',
    'param_insight_context': '当前报告章节的上下文（可选，有助于生成更精准的子问题）',
    'param_panorama_query': '搜索查询，用于相关性排序',
    'param_panorama_expired': '是否包含过期/历史内容（默认True）',
    'param_quick_query': '搜索查询字符串',
    'param_quick_limit': '返回结果数量（可选，默认10）',
    'param_interview_topic': "采访主题或需求描述（如：'了解学生对宿舍甲醛事件的看法'）",
    'param_interview_max': '最多采访的Agent数量（可选，默认5，最大10）',
    'tools_available_prefix': '可用工具：',
    'tools_params_prefix': '  参数: ',

    # ── zep_tools.py: interview fallbacks ──
    'interview_no_profiles': '未找到可采访的Agent人设文件',
    'interview_api_failed': '采访API调用失败：{error}。请检查OASIS模拟环境状态。',
    'interview_failed': '采访失败：{error}。模拟环境可能已关闭，请确保OASIS环境正在运行。',
    'interview_error': '采访过程发生错误：{error}',
    'interview_auto_reason': '基于相关性自动选择',
    'interview_default_strategy': '使用默认选择策略',
    'interview_default_q1': '关于{topic}，您有什么看法？',
    'interview_default_q2': '关于{topic}，您的观点是什么？',
    'interview_default_q3': '这件事对您或您所代表的群体有什么影响？',
    'interview_default_q4': '您认为应该如何解决或改进这个问题？',
    'interview_none_completed': '未完成任何采访',
    'interview_summary_prefix': '共采访了{count}位受访者，包括：',

    # ── zep_tools.py: sub-query fallbacks ──
    'subquery_main_participants': '{query} 的主要参与者',
    'subquery_causes_effects': '{query} 的原因和影响',
    'subquery_development': '{query} 的发展过程',

    # ── oasis_profile_generator.py: fallbacks ──
    'profile_default_country': '中国',
    'profile_persona_fallback': '{name}是一个{type}。',
    'profile_zep_search_query': '关于{entity_name}的所有信息、活动、事件、关系和背景',

    # ── ontology_generator.py: user message building ──
    'ontology_user_sim_req': '## 模拟需求',
    'ontology_user_doc_content': '## 文档内容',
    'ontology_user_extra': '## 额外说明',
    'ontology_user_instruction': (
        "请根据以上内容，设计适合社会舆论模拟的实体类型和关系类型。\n\n"
        "**必须遵守的规则**：\n"
        "1. 必须正好输出10个实体类型\n"
        "2. 最后2个必须是兜底类型：Person（个人兜底）和 Organization（组织兜底）\n"
        "3. 前8个是根据文本内容设计的具体类型\n"
        "4. 所有实体类型必须是现实中可以发声的主体，不能是抽象概念\n"
        "5. 属性名不能使用 name、uuid、group_id 等保留字，用 full_name、org_name 等替代"
    ),
    'ontology_text_truncated': '\n\n...(原文共{original_length}字，已截取前{max_length}字用于本体分析)...',

    # ── simulation_config_generator.py: context building ──
    'sim_config_context_req': '## 模拟需求',
    'sim_config_context_entities': '## 实体信息 ({count}个)',
    'sim_config_context_docs': '## 原始文档内容',
    'sim_config_entity_header': '\n### {type} ({count}个)',
    'sim_config_entity_more': '... 还有 {count} 个',
    'sim_config_doc_truncated': '\n...(文档已截断)',
    'sim_config_default_time_reasoning': '使用默认中国人作息配置（每轮1小时）',
    'sim_config_default_event_reasoning': '使用默认配置',
}

# ═══════════════════════════════════════════════════════════════
# Regex patterns for frontend parsing (must match FORMATS above)
# ═══════════════════════════════════════════════════════════════

PATTERNS = {
    # ── InsightForge parsing ──
    'insight_query': r'分析问题:\s*(.+?)(?:\n|$)',
    'insight_scenario': r'预测场景:\s*(.+?)(?:\n|$)',
    'insight_facts_count': r'相关预测事实:\s*(\d+)',
    'insight_entities_count': r'涉及实体:\s*(\d+)',
    'insight_relations_count': r'关系链:\s*(\d+)',
    'insight_subqueries': r'### 分析的子问题\n([\s\S]*?)(?=\n###|$)',
    'insight_key_facts': r'### 【关键事实】[\s\S]*?\n([\s\S]*?)(?=\n###|$)',
    'insight_entities': r'### 【核心实体】\n([\s\S]*?)(?=\n###|$)',
    'insight_entity_summary': r'摘要:\s*"?(.+?)"?(?:\n|$)',
    'insight_entity_facts': r'相关事实:\s*(\d+)',
    'insight_relations': r'### 【关系链】\n([\s\S]*?)(?=\n###|$)',

    # ── Panorama parsing ──
    'panorama_query': r'查询:\s*(.+?)(?:\n|$)',
    'panorama_nodes': r'总节点数:\s*(\d+)',
    'panorama_edges': r'总边数:\s*(\d+)',
    'panorama_active': r'当前有效事实:\s*(\d+)',
    'panorama_historical': r'历史\/过期事实:\s*(\d+)',
    'panorama_active_section': r'### 【当前有效事实】[\s\S]*?\n([\s\S]*?)(?=\n###|$)',
    'panorama_historical_section': r'### 【历史\/过期事实】[\s\S]*?\n([\s\S]*?)(?=\n###|$)',
    'panorama_entities_section': r'### 【涉及实体】\n([\s\S]*?)(?=\n###|$)',

    # ── Interview parsing ──
    'interview_topic': r'\*\*采访主题:\*\*\s*(.+?)(?:\n|$)',
    'interview_count': r'\*\*采访人数:\*\*\s*(\d+)\s*\/\s*(\d+)',
    'interview_selection': r'### 采访对象选择理由\n([\s\S]*?)(?=\n---\n|\n### 采访实录)',
    'interview_split': r'#### 采访 #\d+:',
    'interview_bio': r'_简介:\s*([\s\S]*?)_\n',
    'interview_twitter': r'【Twitter平台回答】\n?([\s\S]*?)(?=【Reddit平台回答】|$)',
    'interview_reddit': r'【Reddit平台回答】\n?([\s\S]*?)$',
    'interview_quotes': r'\*\*关键引言:\*\*\n([\s\S]*?)(?=\n---|\n####|$)',
    'interview_summary': r'### 采访摘要与核心观点\n([\s\S]*?)$',

    # ── QuickSearch parsing ──
    'quick_query': r'搜索查询:\s*(.+?)(?:\n|$)',
    'quick_count': r'找到\s*(\d+)\s*条',
    'quick_facts': r'### 相关事实:\n([\s\S]*)$',
    'quick_edges': r'### 相关边:\n([\s\S]*?)(?=\n###|$)',
    'quick_nodes': r'### 相关节点:\n([\s\S]*?)(?=\n###|$)',

    # ── Other ──
    'final_answer': r'最终答案[:：]\s*\n*([\s\S]*)$',
    'question_split': r'(?:^|[\r\n]+)问题(\d+)[：:]\s*',
    'question_strip': r'^问题\d+[：:]\s*',
    'platform_no_response': '（该平台未获得回复）',
    'no_reply': '[无回复]',
}
