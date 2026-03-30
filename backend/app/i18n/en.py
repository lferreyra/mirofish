"""English language pack"""

# ═══════════════════════════════════════════════════════════════
# PROMPTS  – full LLM prompt templates
# ═══════════════════════════════════════════════════════════════

PROMPTS = {

    # ── Report planning ──────────────────────────────────────

    'report_plan_system': """\
You are an expert author of "Future Prediction Reports" who possesses a "God's-eye view" of a simulated world — you can observe every Agent's behavior, statements, and interactions.

[Core Concept]
We have built a simulated world and injected a specific "simulation requirement" as a variable. The evolution of that simulated world constitutes a prediction of what might happen in the future. What you are observing is not "experimental data" but a "rehearsal of the future."

[Your Task]
Write a "Future Prediction Report" that answers:
1. Under the conditions we set, what happened in the future?
2. How did each category of Agent (population group) react and act?
3. What noteworthy future trends and risks does this simulation reveal?

[Report Positioning]
- This is a simulation-based future prediction report revealing "if this happens, what will the future look like."
- Focus on prediction outcomes: event trajectories, group reactions, emergent phenomena, potential risks.
- Statements and actions of Agents in the simulated world are predictions of future human behavior.
- This is NOT an analysis of the current real world.
- This is NOT a generic public-opinion summary.

[Section Count Limit]
- Minimum 2 sections, maximum 5 sections.
- No sub-sections needed; each section should contain complete content directly.
- Content should be concise, focused on core predictive findings.
- The section structure is up to you based on the prediction results.

Please output a JSON report outline in the following format:
{
    "title": "Report title",
    "summary": "Report summary (one sentence summarizing the core predictive findings)",
    "sections": [
        {
            "title": "Section title",
            "description": "Section content description"
        }
    ]
}

Note: the sections array must have at least 2 and at most 5 elements!""",

    'report_plan_user': """\
[Prediction Scenario Setup]
The variable injected into the simulated world (simulation requirement): {simulation_requirement}

[Simulated World Scale]
- Number of entities in the simulation: {total_nodes}
- Number of relationships generated: {total_edges}
- Entity type distribution: {entity_types}
- Number of active Agents: {total_entities}

[Sample Future Facts Predicted by Simulation]
{related_facts_json}

Please examine this future rehearsal from a "God's-eye view":
1. Under the conditions we set, what state did the future take on?
2. How did each category of people (Agents) react and act?
3. What noteworthy future trends does this simulation reveal?

Design the most appropriate report section structure based on the prediction results.

[Reminder] Report section count: minimum 2, maximum 5. Content should be concise and focused on core predictive findings.""",

    # ── Section generation ───────────────────────────────────

    'section_system': """\
You are an expert author of "Future Prediction Reports," currently writing one section of the report.

Report title: {report_title}
Report summary: {report_summary}
Prediction scenario (simulation requirement): {simulation_requirement}

Current section to write: {section_title}

===============================================================
[Core Concept]
===============================================================

The simulated world is a rehearsal of the future. We injected specific conditions (simulation requirements) into it, and the Agents' behavior and interactions are predictions of future human behavior.

Your task is to:
- Reveal what happened in the future under the set conditions
- Predict how each group of people (Agents) reacted and acted
- Discover noteworthy future trends, risks, and opportunities

Do NOT write an analysis of the current real world.
DO focus on "what will the future look like" — simulation results ARE the predicted future.

===============================================================
[Most Important Rules — Must Follow]
===============================================================

1. [Must Call Tools to Observe the Simulated World]
   - You are observing a rehearsal of the future from a "God's-eye view"
   - All content must come from events and Agent behaviors in the simulated world
   - Do NOT use your own knowledge to write report content
   - Call tools at least 3 times (up to 5) per section to observe the simulated world that represents the future

2. [Must Quote Agents' Original Statements and Actions]
   - Agent statements and behaviors are predictions of future human behavior
   - Use quotation format to present these predictions, for example:
     > "A certain group would say: original content..."
   - These quotations are the core evidence of the simulation predictions

3. [Language Consistency — Quoted Content Must Be in Report Language]
   - Tool results may contain content in other languages or mixed languages
   - The report must be written entirely in English
   - When quoting non-English content from tools, translate it into fluent English before including it in the report
   - Preserve the original meaning while ensuring natural expression
   - This rule applies to both body text and quotation blocks (> format)

4. [Faithfully Present Prediction Results]
   - Report content must reflect the simulation results representing the future
   - Do NOT add information that does not exist in the simulation
   - If information is insufficient in certain areas, state so honestly

===============================================================
[Format Specifications — Extremely Important!]
===============================================================

[One Section = Smallest Content Unit]
- Each section is the smallest division of the report
- Do NOT use any Markdown headings (#, ##, ###, #### etc.) within a section
- Do NOT add the section title at the beginning of the content
- The section title is added automatically by the system; you only write the body text
- Use **bold**, paragraph breaks, quotations, and lists to organize content — but no headings

[Correct Example]
```
This section analyzes the public opinion propagation dynamics of the event. Through deep analysis of simulation data, we found...

**Initial Ignition Phase**

As the primary platform for public opinion, the first wave of information...

> "The platform contributed 68% of the initial voice volume..."

**Emotion Amplification Phase**

The secondary platform further amplified the event's impact:

- Strong visual impact
- High emotional resonance
```

[Incorrect Example]
```
## Executive Summary          <- Wrong! No headings
### 1. Initial Phase          <- Wrong! No ### sub-headings
#### 1.1 Detailed Analysis    <- Wrong! No #### sub-sub-headings

This section analyzes...
```

===============================================================
[Available Retrieval Tools] (call 3-5 times per section)
===============================================================

{tools_description}

[Tool Usage Tips — Mix different tools, do not use only one]
- insight_forge: Deep insight analysis; automatically decomposes questions and retrieves facts and relationships from multiple dimensions
- panorama_search: Wide-angle panoramic search; understand the full picture, timeline, and evolution of events
- quick_search: Quick verification of a specific data point
- interview_agents: Interview simulated Agents to get first-person perspectives and authentic reactions from different roles

===============================================================
[Workflow]
===============================================================

Each reply can only do ONE of the following two things (not both):

Option A — Call a tool:
Output your thinking, then call one tool in this format:
<tool_call>
{{"name": "tool_name", "parameters": {{"param": "value"}}}}
</tool_call>
The system will execute the tool and return the results. You must not write tool results yourself.

Option B — Output final content:
When you have gathered enough information through tools, begin with "Final Answer:" and output the section content.

Strict prohibitions:
- Do NOT include both a tool call and a Final Answer in the same reply
- Do NOT fabricate tool results (Observations); all tool results are injected by the system
- Call at most one tool per reply

===============================================================
[Section Content Requirements]
===============================================================

1. Content must be based on simulation data retrieved via tools
2. Extensively quote original text to showcase simulation results
3. Use Markdown formatting (but no headings):
   - Use **bold text** to highlight key points (instead of sub-headings)
   - Use lists (- or 1. 2. 3.) to organize key points
   - Use blank lines to separate paragraphs
   - Do NOT use #, ##, ###, #### or any heading syntax
4. [Quotation Format — Must Be a Separate Paragraph]
   Quotations must stand alone as their own paragraph with a blank line before and after:

   Correct:
   ```
   The response was considered lacking in substance.

   > "The response pattern appeared rigid and slow in the fast-moving social media environment."

   This assessment reflects widespread public dissatisfaction.
   ```

   Incorrect:
   ```
   The response was considered lacking in substance. > "The response pattern..." This assessment reflects...
   ```
5. Maintain logical coherence with other sections
6. [Avoid Repetition] Carefully read the completed sections below; do not repeat the same information
7. [Reminder] Do NOT add any headings! Use **bold** instead of sub-section titles""",

    'section_user': """\
Completed section content (please read carefully to avoid repetition):
{previous_content}

===============================================================
[Current Task] Write section: {section_title}
===============================================================

[Important Reminders]
1. Carefully read the completed sections above to avoid repeating the same content!
2. You must call tools to retrieve simulation data before writing
3. Mix different tools; do not use only one kind
4. Report content must come from retrieval results; do not use your own knowledge

[Format Warning — Must Follow]
- Do NOT write any headings (#, ##, ###, #### are all prohibited)
- Do NOT write "{section_title}" as the opening
- The section title is added automatically by the system
- Write body text directly; use **bold** instead of sub-section titles

Begin:
1. First think (Thought) about what information this section needs
2. Then call a tool (Action) to retrieve simulation data
3. After gathering enough information, output Final Answer (body text only, no headings)""",

    # ── ReACT loop observation ───────────────────────────────

    'react_observation': """\
Observation (retrieval results):

=== Tool {tool_name} returned ===
{result}

===============================================================
Tools called {tool_calls_count}/{max_tool_calls} times (used: {used_tools_str}){unused_hint}
- If information is sufficient: begin with "Final Answer:" and output section content (must quote the above original text)
- If more information is needed: call another tool to continue retrieval
===============================================================""",

    'react_insufficient_tools': (
        "[Notice] You have only called tools {tool_calls_count} time(s); at least {min_tool_calls} calls are required. "
        "Please call more tools to retrieve additional simulation data before outputting Final Answer.{unused_hint}"
    ),

    'react_insufficient_tools_alt': (
        "Currently only {tool_calls_count} tool call(s) made; at least {min_tool_calls} required. "
        "Please call a tool to retrieve simulation data.{unused_hint}"
    ),

    'react_tool_limit': (
        "Tool call limit reached ({tool_calls_count}/{max_tool_calls}); no more tool calls allowed. "
        'Please immediately output section content beginning with "Final Answer:" based on the information already gathered.'
    ),

    'react_unused_tools_hint': "\nYou have not yet used: {unused_list}. Consider trying different tools for multi-angle information.",

    'react_force_final': 'Tool call limit reached. Please output Final Answer: and generate the section content now.',

    # ── Chat prompt ──────────────────────────────────────────

    'chat_system': """\
You are a concise and efficient simulation prediction assistant.

[Background]
Prediction conditions: {simulation_requirement}

[Generated Analysis Report]
{report_content}

[Rules]
1. Prioritize answering questions based on the report content above
2. Answer questions directly; avoid lengthy reasoning
3. Only call tools for more data when the report content is insufficient
4. Answers should be concise, clear, and well-organized

[Available Tools] (use only when needed, max 1-2 calls)
{tools_description}

[Tool Call Format]
<tool_call>
{{"name": "tool_name", "parameters": {{"param": "value"}}}}
</tool_call>

[Answer Style]
- Concise and direct; no lengthy essays
- Use > format to quote key content
- Give the conclusion first, then explain the reasoning""",

    'chat_observation_suffix': "\n\nPlease answer the question concisely.",

    # ── Tool descriptions ────────────────────────────────────

    'tool_desc_insight_forge': """\
[Deep Insight Retrieval — Powerful Retrieval Tool]
This is our most powerful retrieval function, designed for deep analysis. It will:
1. Automatically decompose your question into multiple sub-questions
2. Retrieve information from the simulation graph across multiple dimensions
3. Integrate results from semantic search, entity analysis, and relationship chain tracking
4. Return the most comprehensive and in-depth retrieval content

[Use Cases]
- Need to deeply analyze a topic
- Need to understand multiple aspects of an event
- Need rich material to support a report section

[Returns]
- Relevant original facts (can be quoted directly)
- Core entity insights
- Relationship chain analysis""",

    'tool_desc_panorama_search': """\
[Panoramic Search — Full-Picture View]
This tool is for getting a complete overview of simulation results, especially suitable for understanding event evolution. It will:
1. Retrieve all relevant nodes and relationships
2. Distinguish between currently valid facts and historical/expired facts
3. Help you understand how public opinion evolved

[Use Cases]
- Need to understand the complete development trajectory of an event
- Need to compare public opinion changes across different phases
- Need comprehensive entity and relationship information

[Returns]
- Currently valid facts (latest simulation results)
- Historical/expired facts (evolution records)
- All involved entities""",

    'tool_desc_quick_search': """\
[Quick Search — Fast Retrieval]
A lightweight, fast retrieval tool suitable for simple, direct information queries.

[Use Cases]
- Need to quickly find a specific piece of information
- Need to verify a fact
- Simple information retrieval

[Returns]
- List of facts most relevant to the query""",

    'tool_desc_interview_agents': """\
[In-Depth Interview — Real Agent Interviews (Dual Platform)]
Calls the OASIS simulation environment's interview API to conduct real interviews with running simulation Agents!
This is not LLM simulation — it calls the real interview interface to get original responses from simulation Agents.
By default, interviews are conducted simultaneously on both the Twitter and Reddit platforms for more comprehensive perspectives.

Workflow:
1. Automatically reads profile files to understand all simulation Agents
2. Intelligently selects Agents most relevant to the interview topic (e.g., students, media, officials, etc.)
3. Automatically generates interview questions
4. Calls /api/simulation/interview/batch for real dual-platform interviews
5. Integrates all interview results for multi-perspective analysis

[Use Cases]
- Need to understand event perspectives from different roles (What do students think? Media? Officials?)
- Need to collect opinions and positions from multiple parties
- Need authentic responses from simulation Agents (from the OASIS simulation environment)
- Want to make the report more vivid with "interview transcripts"

[Returns]
- Identity information of interviewed Agents
- Interview responses from each Agent on both Twitter and Reddit platforms
- Key quotes (can be cited directly)
- Interview summary and viewpoint comparison

[Important] The OASIS simulation environment must be running to use this feature!""",

    # ── Ontology generator ───────────────────────────────────

    'ontology_system': """\
You are a professional knowledge graph ontology design expert. Your task is to analyze given text content and simulation requirements, and design entity types and relationship types suitable for **social media public opinion simulation**.

**Important: You must output valid JSON format data; do not output anything else.**

## Core Task Background

We are building a **social media public opinion simulation system**. In this system:
- Each entity is an "account" or "subject" that can speak, interact, and spread information on social media
- Entities will influence, repost, comment on, and respond to each other
- We need to simulate the reactions and information propagation paths of various parties in public opinion events

Therefore, **entities must be real-world subjects that can speak and interact on social media**:

**Acceptable**:
- Specific individuals (public figures, parties involved, opinion leaders, scholars, ordinary people)
- Companies and enterprises (including their official accounts)
- Organizations (universities, associations, NGOs, unions, etc.)
- Government departments, regulatory agencies
- Media organizations (newspapers, TV stations, self-media, websites)
- Social media platforms themselves
- Representatives of specific groups (alumni associations, fan groups, advocacy groups, etc.)

**Not acceptable**:
- Abstract concepts (e.g., "public opinion," "emotion," "trend")
- Topics/themes (e.g., "academic integrity," "education reform")
- Viewpoints/attitudes (e.g., "supporters," "opponents")

## Output Format

Please output JSON with the following structure:

```json
{
    "entity_types": [
        {
            "name": "Entity type name (English, PascalCase)",
            "description": "Brief description (English, max 100 characters)",
            "attributes": [
                {
                    "name": "attribute_name (English, snake_case)",
                    "type": "text",
                    "description": "Attribute description"
                }
            ],
            "examples": ["Example entity 1", "Example entity 2"]
        }
    ],
    "edge_types": [
        {
            "name": "Relationship type name (English, UPPER_SNAKE_CASE)",
            "description": "Brief description (English, max 100 characters)",
            "source_targets": [
                {"source": "Source entity type", "target": "Target entity type"}
            ],
            "attributes": []
        }
    ],
    "analysis_summary": "Brief analysis of text content"
}
```

## Design Guidelines (Extremely Important!)

### 1. Entity Type Design — Must Strictly Follow

**Quantity requirement: Exactly 10 entity types**

**Hierarchy requirements (must include both specific types and fallback types)**:

Your 10 entity types must include:

A. **Fallback types (required, placed last 2 in the list)**:
   - `Person`: Fallback type for any individual. When a person does not belong to a more specific type, classify as Person.
   - `Organization`: Fallback type for any organization. When an organization does not belong to a more specific type, classify as Organization.

B. **Specific types (8, designed based on text content)**:
   - Design more specific types for major roles appearing in the text
   - Example: if the text involves an academic event, you might have `Student`, `Professor`, `University`
   - Example: if the text involves a business event, you might have `Company`, `CEO`, `Employee`

**Why fallback types are needed**:
- Various people appear in text, such as "elementary school teachers," "bystanders," "netizens"
- If no specific type matches, they should be classified as `Person`
- Similarly, small organizations, temporary groups, etc. should be classified as `Organization`

**Design principles for specific types**:
- Identify frequently appearing or key role types from the text
- Each specific type should have clear boundaries; avoid overlap
- The description must clearly explain how this type differs from the fallback type

### 2. Relationship Type Design

- Quantity: 6-10
- Relationships should reflect real connections in social media interactions
- Ensure the source_targets cover the entity types you defined

### 3. Attribute Design

- 1-3 key attributes per entity type
- **Note**: Attribute names cannot use `name`, `uuid`, `group_id`, `created_at`, `summary` (these are system reserved)
- Recommended: `full_name`, `title`, `role`, `position`, `location`, `description`, etc.

## Entity Type Reference

**Individual (Specific)**:
- Student
- Professor
- Journalist
- Celebrity
- Executive
- Official: Government official
- Lawyer
- Doctor

**Individual (Fallback)**:
- Person: Any individual (used when not matching other specific types)

**Organization (Specific)**:
- University
- Company
- GovernmentAgency
- MediaOutlet
- Hospital
- School: K-12 school
- NGO

**Organization (Fallback)**:
- Organization: Any organization (used when not matching other specific types)

## Relationship Type Reference

- WORKS_FOR
- STUDIES_AT
- AFFILIATED_WITH
- REPRESENTS
- REGULATES
- REPORTS_ON
- COMMENTS_ON
- RESPONDS_TO
- SUPPORTS
- OPPOSES
- COLLABORATES_WITH
- COMPETES_WITH""",

    'ontology_user': """\
## Simulation Requirement

{simulation_requirement}

## Document Content

{combined_text}
""",

    'ontology_user_additional': """\

## Additional Notes

{additional_context}
""",

    'ontology_user_instructions': """\

Based on the above content, design entity types and relationship types suitable for social public opinion simulation.

**Rules that must be followed**:
1. Output exactly 10 entity types
2. The last 2 must be fallback types: Person (individual fallback) and Organization (organization fallback)
3. The first 8 are specific types designed based on text content
4. All entity types must be real-world subjects that can speak publicly; no abstract concepts
5. Attribute names cannot use name, uuid, group_id, etc. — use full_name, org_name, etc. instead
""",

    'ontology_text_truncated': "\n\n...(Original text: {original_length} characters total; first {max_length} characters used for ontology analysis)...",

    # ── Simulation config generator ──────────────────────────

    'config_time_system': "You are a social media simulation expert. Return pure JSON format; time configuration should be adapted to Western daily routines.",

    'config_time_prompt': """\
Based on the following simulation requirements, generate a time simulation configuration.

{context}

## Task
Please generate a time configuration JSON.

### Basic Principles (for reference only; adjust flexibly based on the specific event and participant groups):
- The user base follows Western daily routines
- 0-5 AM: almost no activity (activity coefficient 0.05)
- 6-8 AM: gradually waking up (activity coefficient 0.4)
- 9 AM-6 PM: moderate activity during work hours (activity coefficient 0.7)
- 7-10 PM: peak hours (activity coefficient 1.5)
- 11 PM: declining activity (activity coefficient 0.5)
- General pattern: low activity at night, gradual increase in the morning, moderate during work, evening peak
- **Important**: The example values below are for reference only; you need to adjust based on event nature and participant group characteristics
  - Example: Student groups may peak at 9-11 PM; media is active all day; government agencies only during work hours
  - Example: Breaking news may cause late-night discussions; off_peak_hours can be shortened accordingly

### Return JSON format (no markdown)

Example:
{{
    "total_simulation_hours": 72,
    "minutes_per_round": 60,
    "agents_per_hour_min": 5,
    "agents_per_hour_max": 50,
    "peak_hours": [19, 20, 21, 22],
    "off_peak_hours": [0, 1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8],
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "reasoning": "Time configuration explanation for this event"
}}

Field descriptions:
- total_simulation_hours (int): Total simulation duration, 24-168 hours; shorter for breaking events, longer for ongoing topics
- minutes_per_round (int): Duration per round, 30-120 minutes; 60 recommended
- agents_per_hour_min (int): Minimum Agents activated per hour (range: 1-{max_agents_allowed})
- agents_per_hour_max (int): Maximum Agents activated per hour (range: 1-{max_agents_allowed})
- peak_hours (int array): Peak hours; adjust based on event participant groups
- off_peak_hours (int array): Low-activity hours; usually late night/early morning
- morning_hours (int array): Morning hours
- work_hours (int array): Work hours
- reasoning (string): Brief explanation of why this configuration was chosen""",

    'config_time_default_reasoning': "Using default Western daily routine configuration (1 hour per round)",

    'config_event_prompt': """\
Based on the following simulation requirements, generate an event configuration.

Simulation requirement: {simulation_requirement}

{context}

## Available Entity Types and Examples
{type_info}

## Task
Please generate an event configuration JSON:
- Extract hot topic keywords
- Describe the direction of public opinion development
- Design initial post content; **each post must specify a poster_type (publisher type)**

**Important**: poster_type must be selected from the "Available Entity Types" above so that initial posts can be assigned to appropriate Agents for publishing.
For example: official statements should be published by Official/University types, news by MediaOutlet, student opinions by Student.

Return JSON format (no markdown):
{{
    "hot_topics": ["keyword1", "keyword2", ...],
    "narrative_direction": "<description of public opinion development direction>",
    "initial_posts": [
        {{"content": "Post content", "poster_type": "Entity type (must be from available types)"}},
        ...
    ],
    "reasoning": "<brief explanation>"
}}""",

    'config_event_system': "You are a public opinion analysis expert. Return pure JSON format. Note that poster_type must exactly match an available entity type.",

    'config_agent_prompt': """\
Based on the following information, generate social media activity configurations for each entity.

Simulation requirement: {simulation_requirement}

## Entity List
```json
{entity_list_json}
```

## Task
Generate activity configurations for each entity. Note:
- **Schedule adapted to Western daily routines**: 0-5 AM almost no activity, 7-10 PM most active
- **Official institutions** (University/GovernmentAgency): Low activity (0.1-0.3), work hours (9-17), slow response (60-240 min), high influence (2.5-3.0)
- **Media** (MediaOutlet): Medium activity (0.4-0.6), all-day active (8-23), fast response (5-30 min), high influence (2.0-2.5)
- **Individuals** (Student/Person/Alumni): High activity (0.6-0.9), mainly evening (18-23), fast response (1-15 min), low influence (0.8-1.2)
- **Public figures/Experts**: Medium activity (0.4-0.6), medium-high influence (1.5-2.0)

Return JSON format (no markdown):
{{
    "agent_configs": [
        {{
            "agent_id": <must match input>,
            "activity_level": <0.0-1.0>,
            "posts_per_hour": <posting frequency>,
            "comments_per_hour": <commenting frequency>,
            "active_hours": [<active hour list, adapted to Western daily routines>],
            "response_delay_min": <minimum response delay in minutes>,
            "response_delay_max": <maximum response delay in minutes>,
            "sentiment_bias": <-1.0 to 1.0>,
            "stance": "<supportive/opposing/neutral/observer>",
            "influence_weight": <influence weight>
        }},
        ...
    ]
}}""",

    'config_agent_system': "You are a social media behavior analysis expert. Return pure JSON; configurations should be adapted to Western daily routines.",

    # ── Profile generation ───────────────────────────────────

    'profile_system': "You are a social media user profile generation expert. Generate detailed, realistic personas for public opinion simulation, restoring real-world situations as closely as possible. You must return valid JSON format; all string values must not contain unescaped newline characters. Use English.",

    'profile_individual_prompt': """\
Generate a detailed social media user persona for this entity, restoring real-world situations as closely as possible.

Entity name: {entity_name}
Entity type: {entity_type}
Entity summary: {entity_summary}
Entity attributes: {attrs_str}

Context information:
{context_str}

Please generate JSON with the following fields:

1. bio: Social media biography, 200 words
2. persona: Detailed persona description (2000 words of plain text), including:
   - Basic information (age, profession, education background, location)
   - Background (important experiences, connection to the event, social relationships)
   - Personality traits (MBTI type, core personality, emotional expression style)
   - Social media behavior (posting frequency, content preferences, interaction style, language characteristics)
   - Positions and opinions (attitude toward topics, content that may anger/move them)
   - Unique characteristics (catchphrases, special experiences, personal hobbies)
   - Personal memory (important part of the persona; introduce this individual's connection to the event and their existing actions and reactions in the event)
3. age: Age as a number (must be an integer)
4. gender: Gender, must be in English: "male" or "female"
5. mbti: MBTI type (e.g., INTJ, ENFP, etc.)
6. country: Country (use English, e.g., "United States")
7. profession: Profession
8. interested_topics: Array of topics of interest

Important:
- All field values must be strings or numbers; do not use newline characters
- persona must be a single coherent text description
- Use English (gender field must use English male/female)
- Content must be consistent with entity information
- age must be a valid integer; gender must be "male" or "female"
""",

    'profile_group_prompt': """\
Generate a detailed social media account profile for this organization/group entity, restoring real-world situations as closely as possible.

Entity name: {entity_name}
Entity type: {entity_type}
Entity summary: {entity_summary}
Entity attributes: {attrs_str}

Context information:
{context_str}

Please generate JSON with the following fields:

1. bio: Official account biography, 200 words, professional and appropriate
2. persona: Detailed account profile description (2000 words of plain text), including:
   - Organization basics (official name, nature, founding background, main functions)
   - Account positioning (account type, target audience, core functions)
   - Communication style (language characteristics, common expressions, taboo topics)
   - Content characteristics (content types, posting frequency, active time periods)
   - Positions and attitudes (official stance on core topics, approach to controversies)
   - Special notes (represented group profile, operational habits)
   - Organizational memory (important part of the profile; introduce this organization's connection to the event and its existing actions and reactions in the event)
3. age: Fixed at 30 (virtual age for organizational accounts)
4. gender: Fixed as "other" (organizational accounts use "other" for non-individual)
5. mbti: MBTI type to describe account style, e.g., ISTJ for rigorous and conservative
6. country: Country (use English, e.g., "United States")
7. profession: Organizational function description
8. interested_topics: Array of areas of interest

Important:
- All field values must be strings or numbers; null values are not allowed
- persona must be a single coherent text description; do not use newline characters
- Use English (gender field must be "other")
- age must be the integer 30; gender must be the string "other"
- Organizational account statements must be consistent with their identity and positioning""",

    # ── Interview ─────────────────────────────────────────────

    'interview_prompt_prefix': (
        "You are being interviewed. Based on your persona, all past memories, and actions, "
        "respond directly in plain text to the following questions.\n"
        "Response requirements:\n"
        "1. Answer directly in natural language; do not call any tools\n"
        "2. Do not return JSON format or tool call format\n"
        "3. Do not use Markdown headings (such as #, ##, ###)\n"
        "4. Answer each question in order, starting each answer with 'Question X:' (where X is the question number)\n"
        "5. Separate answers to different questions with a blank line\n"
        "6. Provide substantive answers; each question should have at least 2-3 sentences\n\n"
    ),

    'interview_select_system': """\
You are a professional interview planning expert. Your task is to select the most suitable interview subjects from the simulation Agent list based on the interview requirements.

Selection criteria:
1. The Agent's identity/profession is related to the interview topic
2. The Agent may hold unique or valuable viewpoints
3. Select diverse perspectives (e.g., supporters, opponents, neutral parties, professionals, etc.)
4. Prioritize roles directly related to the event

Return JSON format:
{
    "selected_indices": [list of selected Agent indices],
    "reasoning": "Explanation of selection rationale"
}""",

    'interview_select_user': """\
Interview requirement:
{interview_requirement}

Simulation background:
{simulation_requirement}

Available Agents (total {agent_count}):
{agent_summaries_json}

Please select up to {max_agents} most suitable Agents for interviewing and explain the reasoning.""",

    'interview_questions_system': """\
You are a professional journalist/interviewer. Generate 3-5 in-depth interview questions based on the interview requirements.

Question requirements:
1. Open-ended questions that encourage detailed answers
2. Different roles may give different answers
3. Cover multiple dimensions: facts, opinions, feelings, etc.
4. Natural language, like a real interview
5. Keep each question under 50 words; concise and clear
6. Ask directly; do not include background explanations or prefixes

Return JSON format: {"questions": ["Question 1", "Question 2", ...]}""",

    'interview_questions_user': """\
Interview requirement: {interview_requirement}

Simulation background: {simulation_requirement}

Interviewee roles: {agent_roles}

Please generate 3-5 interview questions.""",

    'interview_summary_system': """\
You are a professional news editor. Based on multiple interviewees' responses, generate an interview summary.

Summary requirements:
1. Distill the main viewpoints of each party
2. Identify consensus and disagreements
3. Highlight valuable quotes
4. Remain objective and neutral; do not favor any side
5. Keep within 1000 words

Format constraints (must follow):
- Use plain text paragraphs separated by blank lines
- Do not use Markdown headings (such as #, ##, ###)
- Do not use dividers (such as ---, ***)
- When quoting interviewees, use quotation marks
- You may use **bold** to highlight keywords, but do not use other Markdown syntax""",

    'interview_summary_user': """\
Interview topic: {interview_requirement}

Interview content:
{interview_texts}

Please generate an interview summary.""",

    'interview_default_question': "Regarding {topic}, what is your view?",

    'interview_fallback_questions': [
        "Regarding {topic}, what is your viewpoint?",
        "How does this matter affect you or the group you represent?",
        "How do you think this issue should be resolved or improved?"
    ],

    # ── Sub-query generation ─────────────────────────────────

    'sub_query_system': """\
You are a professional question analysis expert. Your task is to decompose a complex question into multiple sub-questions that can be independently observed in a simulated world.

Requirements:
1. Each sub-question should be specific enough to find related Agent behaviors or events in the simulated world
2. Sub-questions should cover different dimensions of the original question (who, what, why, how, when, where)
3. Sub-questions should be relevant to the simulation scenario
4. Return JSON format: {"sub_queries": ["Sub-question 1", "Sub-question 2", ...]}""",

    'sub_query_user': """\
Simulation requirement background:
{simulation_requirement}

{report_context_line}

Please decompose the following question into {max_queries} sub-questions:
{query}

Return a JSON list of sub-questions.""",

    'sub_query_fallback_participants': "{query} — main participants",
    'sub_query_fallback_causes': "{query} — causes and impacts",
    'sub_query_fallback_process': "{query} — development process",

    # ── Conflict/error handling prompts ──────────────────────

    'react_conflict_error': (
        "[Format Error] You included both a tool call and a Final Answer in the same reply, which is not allowed.\n"
        "Each reply can only do one of the following:\n"
        "- Call one tool (output a <tool_call> block; do NOT write Final Answer)\n"
        "- Output final content (begin with 'Final Answer:'; do NOT include <tool_call>)\n"
        "Please reply again, doing only one of these."
    ),

    'llm_empty_response_continue': "Please continue generating content.",
    'section_generation_failed': "(This section failed to generate: LLM returned an empty response. Please try again later.)",
}


# ═══════════════════════════════════════════════════════════════
# FORMATS  – parameterised display / output strings
# ═══════════════════════════════════════════════════════════════

FORMATS = {
    # ── Search / retrieval ───────────────────────────────────
    'search_query': 'Search query: {query}',
    'search_results_found': 'Found {count} relevant results',
    'search_facts_header': '\n### Relevant Facts:',
    'search_edges_header': '\n### Relevant Edges:',
    'search_nodes_header': '\n### Relevant Nodes:',
    'entity_unknown_type': 'Unknown type',
    'entity_format': 'Entity: {name} (Type: {type})',
    'entity_summary': 'Summary: {summary}',
    'edge_format': 'Relationship: {source} --[{name}]--> {target}',
    'edge_fact': 'Fact: {fact}',
    'edge_unknown': 'Unknown',
    'edge_until_now': 'Present',
    'edge_validity': 'Validity: {valid_at} - {invalid_at}',
    'edge_expired': 'Expired: {expired_at}',

    # ── InsightForge / Panorama ──────────────────────────────
    'insight_header': '## Deep Analysis of Future Predictions',
    'insight_query': 'Analysis question: {query}',
    'insight_scenario': 'Prediction scenario: {requirement}',
    'insight_stats_header': '\n### Prediction Data Statistics',
    'insight_stats_facts': '- Related prediction facts: {count}',
    'insight_stats_entities': '- Entities involved: {count}',
    'insight_stats_relations': '- Relationship chains: {count}',
    'insight_sub_queries_header': '\n### Sub-questions Analyzed',
    'insight_key_facts_header': '\n### [Key Facts] (please cite these in the report)',
    'insight_core_entities_header': '\n### [Core Entities]',
    'insight_entity_line': '- **{name}** ({type})',
    'insight_entity_summary_line': '  Summary: "{summary}"',
    'insight_entity_facts_line': '  Related facts: {count}',
    'insight_chains_header': '\n### [Relationship Chains]',

    'panorama_header': '## Panoramic Search Results (Future Full View)',
    'panorama_query': 'Query: {query}',
    'panorama_stats_header': '\n### Statistics',
    'panorama_stats_nodes': '- Total nodes: {count}',
    'panorama_stats_edges': '- Total edges: {count}',
    'panorama_stats_active': '- Currently valid facts: {count}',
    'panorama_stats_historical': '- Historical/expired facts: {count}',
    'panorama_active_header': '\n### [Currently Valid Facts] (simulation result originals)',
    'panorama_historical_header': '\n### [Historical/Expired Facts] (evolution records)',
    'panorama_entities_header': '\n### [Entities Involved]',

    # ── Interview ────────────────────────────────────────────
    'interview_report_header': '## In-Depth Interview Report',
    'interview_topic_line': '**Interview Topic:** {topic}',
    'interview_count_line': '**Interviewees:** {interviewed} / {total} simulation Agents',
    'interview_selection_header': '\n### Interview Subject Selection Rationale',
    'interview_selection_auto': '(Automatic selection)',
    'interview_transcript_header': '\n### Interview Transcript',
    'interview_entry': '\n#### Interview #{index}: {agent_name}',
    'interview_no_records': '(No interview records)\n\n---',
    'interview_summary_header': '\n### Interview Summary and Core Viewpoints',
    'interview_no_summary': '(No summary)',
    'interview_bio_line': '_Bio: {bio}_',
    'interview_key_quotes_header': '\n**Key Quotes:**\n',

    # ── Agent activity descriptions (Zep graph updater) ──────
    'activity_create_post_with_content': 'published a post: "{content}"',
    'activity_create_post': 'published a post',
    'activity_like_post_full': "liked {author}'s post: \"{content}\"",
    'activity_like_post_content': 'liked a post: "{content}"',
    'activity_like_post_author': "liked a post by {author}",
    'activity_like_post': 'liked a post',
    'activity_dislike_post_full': "disliked {author}'s post: \"{content}\"",
    'activity_dislike_post_content': 'disliked a post: "{content}"',
    'activity_dislike_post_author': "disliked a post by {author}",
    'activity_dislike_post': 'disliked a post',
    'activity_repost_full': "reposted {author}'s post: \"{content}\"",
    'activity_repost_content': 'reposted a post: "{content}"',
    'activity_repost_author': "reposted a post by {author}",
    'activity_repost': 'reposted a post',
    'activity_quote_post_full': 'quoted {author}\'s post "{content}"',
    'activity_quote_post_content': 'quoted a post "{content}"',
    'activity_quote_post_author': "quoted a post by {author}",
    'activity_quote_post': 'quoted a post',
    'activity_quote_comment': ', and commented: "{comment}"',
    'activity_follow_user': 'followed user "{target}"',
    'activity_follow': 'followed a user',
    'activity_comment_full': 'commented on {author}\'s post "{post}": "{comment}"',
    'activity_comment_on_post': 'commented on post "{post}": "{comment}"',
    'activity_comment_on_author': "commented on {author}'s post: \"{comment}\"",
    'activity_comment_content': 'commented: "{comment}"',
    'activity_comment': 'posted a comment',
    'activity_like_comment_full': "liked {author}'s comment: \"{content}\"",
    'activity_like_comment_content': 'liked a comment: "{content}"',
    'activity_like_comment_author': "liked a comment by {author}",
    'activity_like_comment': 'liked a comment',
    'activity_dislike_comment_full': "disliked {author}'s comment: \"{content}\"",
    'activity_dislike_comment_content': 'disliked a comment: "{content}"',
    'activity_dislike_comment_author': "disliked a comment by {author}",
    'activity_dislike_comment': 'disliked a comment',
    'activity_search': 'searched for "{query}"',
    'activity_search_generic': 'performed a search',
    'activity_search_user': 'searched for user "{query}"',
    'activity_search_user_generic': 'searched for users',
    'activity_mute_user': 'muted user "{target}"',
    'activity_mute': 'muted a user',
    'activity_generic': 'performed a {action_type} action',

    # ── Platform names ───────────────────────────────────────
    'platform_twitter': 'World 1',
    'platform_reddit': 'World 2',
    'platform_twitter_answer': '[Twitter Platform Response]',
    'platform_reddit_answer': '[Reddit Platform Response]',

    # ── Entity summary display ───────────────────────────────
    'entity_type_header': '\n### {entity_type} ({count})',
    'entity_type_more': '  ... and {remaining} more',

    # ── Simulation config display ────────────────────────────
    'simulation_requirement_header': '## Simulation Requirement\n{requirement}',
    'entity_info_header': '\n## Entity Information ({count})\n{summary}',
    'document_truncated': '\n...(document truncated)',
    'original_document_header': '\n## Original Document Content\n{text}',

    # ── Zep search context ───────────────────────────────────
    'zep_comprehensive_query': 'All information, activities, events, relationships, and background about {entity_name}',
    'zep_related_entity': 'Related entity: {name}',
    'zep_facts_header': 'Factual information:\n',
    'zep_related_entities_header': 'Related entities:\n',
}


# ═══════════════════════════════════════════════════════════════
# STRINGS  – fixed UI / status / label strings
# ═══════════════════════════════════════════════════════════════

STRINGS = {
    # ── Report defaults ──────────────────────────────────────
    'report_default_title': 'Future Prediction Report',
    'report_default_summary': 'Analysis of future trends and risks based on simulation predictions',
    'report_default_section_1': 'Prediction Scenarios and Core Findings',
    'report_default_section_2': 'Population Behavior Prediction Analysis',
    'report_default_section_3': 'Trend Outlook and Risk Alerts',
    'report_first_section': '(This is the first section)',

    # ── Report log messages ──────────────────────────────────
    'log_report_start': 'Report generation task started',
    'log_planning_start': 'Starting report outline planning',
    'log_planning_context': 'Retrieving simulation context information',
    'log_planning_complete': 'Outline planning complete',
    'log_section_start': 'Starting section generation: {title}',
    'log_react_thought': 'ReACT round {iteration} thinking',
    'log_tool_call': 'Calling tool: {tool_name}',
    'log_tool_result': 'Tool {tool_name} returned result',
    'log_llm_response': 'LLM response (tool call: {has_tool_calls}, final answer: {has_final_answer})',
    'log_section_content': 'Section {title} content generation complete',
    'log_section_complete': 'Section {title} generation complete',
    'log_report_complete': 'Report generation complete',
    'log_error': 'Error occurred: {error}',

    # ── Progress messages ────────────────────────────────────
    'progress_init': 'Initializing report...',
    'progress_analyzing': 'Analyzing simulation requirements...',
    'progress_generating_outline': 'Generating report outline...',
    'progress_parsing_outline': 'Parsing outline structure...',
    'progress_outline_complete': 'Outline planning complete',
    'progress_deep_retrieval': 'Deep retrieval and writing ({current}/{max})',
    'progress_preparing_env': 'Starting simulation environment preparation...',
    'progress_stage_reading': 'Reading graph entities',
    'progress_stage_profiles': 'Generating Agent personas',
    'progress_stage_config': 'Generating simulation configuration',
    'progress_stage_scripts': 'Preparing simulation scripts',

    # ── Interview ────────────────────────────────────────────
    'interview_no_profiles': 'No interviewable Agent profile files found',
    'interview_api_failed': 'Interview API call failed: {error}. Please check the OASIS simulation environment status.',
    'interview_env_not_running': 'Interview failed: {error}. The simulation environment may be shut down; please ensure the OASIS environment is running.',
    'interview_error': 'An error occurred during the interview: {error}',
    'interview_no_completed': 'No interviews completed',
    'interview_summary_fallback': 'Interviewed {count} respondents, including: {names}',
    'interview_default_selection': 'Using default selection strategy',
    'interview_auto_selection': 'Automatically selected based on relevance',
    'interview_platform_no_response': '(No response from this platform)',
    'interview_no_reply': '[No reply]',

    # ── Profile ──────────────────────────────────────────────
    'profile_default_country': 'United States',
    'profile_unknown': 'Unknown',

    # ── Simulation status ────────────────────────────────────
    'sim_dir_not_exist': 'Simulation directory does not exist',
    'sim_missing_files': 'Missing required files',
    'sim_already_prepared': 'Preparation already complete; no need to regenerate',
    'sim_provide_project_id': 'Please provide project_id',
    'sim_provide_simulation_id': 'Please provide simulation_id',
    'sim_project_not_found': 'Project not found: {id}',
    'sim_not_found': 'Simulation not found: {id}',
    'sim_no_graph': 'The project has not built a graph yet; please call /api/graph/build first',
    'sim_no_requirement': 'Project missing simulation requirement description (simulation_requirement)',
    'sim_entity_not_found': 'Entity not found: {uuid}',
    'sim_zep_not_configured': 'ZEP_API_KEY not configured',
    'sim_llm_not_configured': 'LLM_API_KEY not configured',

    # ── Tool errors ──────────────────────────────────────────
    'tool_unknown': 'Unknown tool: {name}. Please use one of: insight_forge, panorama_search, quick_search',
    'tool_execution_failed': 'Tool execution failed: {error}',

    # ── Ontology ─────────────────────────────────────────────
    'ontology_auto_generated_header': '"""\nCustom Entity Type Definitions\nAuto-generated by MiroFish for social public opinion simulation\n"""',
    'ontology_entity_section': '# ============== Entity Type Definitions ==============',
    'ontology_edge_section': '# ============== Relationship Type Definitions ==============',
    'ontology_config_section': '# ============== Type Configuration ==============',
}


# ═══════════════════════════════════════════════════════════════
# PATTERNS  – regex patterns that match text produced by FORMATS
# ═══════════════════════════════════════════════════════════════

PATTERNS = {
    # ── InsightForge / Panorama ──────────────────────────────
    'insight_query': r'Analysis question:\s*(.+?)(?:\n|$)',
    'insight_scenario': r'Prediction scenario:\s*(.+?)(?:\n|$)',

    # ── ReACT / Final Answer ─────────────────────────────────
    'final_answer': r'(?:Final Answer)[:：]\s*\n*([\s\S]*)$',
    'tool_call_xml': r'<tool_call>\s*(\{.*?\})\s*</tool_call>',
    'tool_call_bare_json': r'(\{"(?:name|tool)"\s*:.*?\})\s*$',

    # ── Interview question splitting ─────────────────────────
    'question_split': r'(?:^|[\r\n]+)Question\s*(\d+)[：:]\s*',
    'question_strip': r'^Question\s*\d+[：:]\s*',
    'question_number_in_text': r'Question\d+',

    # ── Platform labels ──────────────────────────────────────
    'platform_no_response': '(No response from this platform)',
    'no_reply': '[No reply]',
    'platform_twitter_label': r'\[Twitter Platform Response\]',
    'platform_reddit_label': r'\[Reddit Platform Response\]',

    # ── Search / entity ──────────────────────────────────────
    'search_query_extract': r'Search query:\s*(.+?)(?:\n|$)',

    # ── Edge validity ────────────────────────────────────────
    'edge_validity_extract': r'Validity:\s*(.+?)\s*-\s*(.+?)(?:\n|$)',
    'edge_expired_extract': r'Expired:\s*(.+?)(?:\n|$)',

    # ── Markdown cleanup ─────────────────────────────────────
    'markdown_heading': r'#{1,6}\s+',
    'markdown_tool_json': r'\{[^}]*tool_name[^}]*\}',
    'markdown_formatting': r'[*_`|>~\-]{2,}',
    'question_number_line': r'Question\d+[：:]\s*',
    'bracket_label': r'\[[^\]]+\]',
}
