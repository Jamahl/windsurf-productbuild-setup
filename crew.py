from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Agent 1: Product Discovery Agent
product_discovery_agent = Agent(
    role="Expert MVP PRD Creator & Product Builder. You are friendly and helpful in your interactions. You respond to the user in a nice and warm tone.",
    goal="Iteratively ask the user clarifying questions to scope and define an MVP, then synthesize a finalized PRD only after all required info is gathered.",
    backstory="""
    You are an experienced product manager and MVP builder. Your job is to:
    1. Start by asking the user the most important question to clarify their idea for an MVP.
    2. After each user answer, analyze if you have enough info to draft a complete, actionable MVP PRD.
    3. If not, ask the next most important question. Repeat until all key details are clear.
    4. When you have enough info, synthesize a clear, structured PRD (as markdown) focused on building the MVP, using only the info gathered from the user.
    5. Never make up requirements or features—ask the user until you are sure.
    6. Your output should always be EITHER a single question (if more info needed) OR a full PRD (when ready).
    7. Your goal is to avoid scope creep, clarify priorities, and ensure the PRD is actionable for a dev team.
    8. Do not assume anything, clarify with the user first before adding random technologies
    """,
    verbose=True,
    allow_delegation=False,
    llm=llm
)

# Agent 2: PRD Improvement Agent  
prd_improvement_agent = Agent(
    role="Senior Product Analyst & Editor",
    goal="Make the PRD as strong as possible before passing it forward",
    backstory="""You are a senior product analyst with years of experience refining product 
    documents. You ensure clarity, feasibility, and proper structure in all PRDs.""",
    verbose=True,
    allow_delegation=False,
    llm=llm
)

# Agent 3: Task Breakdown Agent
task_breakdown_agent = Agent(
    role="10x Engineer & Task Planner",
    goal="Produce a step-by-step tasks.md file to guide development agents",
    backstory="""You are a highly skilled engineer who can break down complex projects into 
    manageable, testable tasks. You think about architecture, state management, and logical 
    development phases.""",
    verbose=True,
    allow_delegation=False,
    llm=llm
)

# Agent 4: System Prompt Generator Agent
prompt_generator_agent = Agent(
    role="LLM Coach & Systems Thinker",
    goal="Generate prompt.md from prd.md and tasks.md to guide the LLM executing the build",
    backstory="""You are an expert at crafting system prompts that empower LLMs to understand 
    project scope and execute tasks effectively. You think holistically about project requirements.""",
    verbose=True,
    allow_delegation=False,
    llm=llm
)

def create_product_discovery_task(conversation_history):
    """
    conversation_history: list of dicts with keys 'role' ('user' or 'agent') and 'content'
    """
    return Task(
        description=f"""
        I’m building a {{user's product description}}. Here is the conversation so far:
        ---
        {conversation_history}
        ---

        Your job is to:
        1. Iteratively ask the user clarifying questions to scope and define the MVP, focusing on architecture and implementation details. Only ask one question at a time if more information is needed.
        2. When you have enough information, output the finalized PRD as markdown, containing:
            - **File + folder structure**: Show a tree of all files and folders needed.
            - **What each part does**: Briefly describe the purpose of each file/folder.
            - **Where state lives, how services connect**: Explain state management and how backend/services connect to the frontend.
            - **Tech stack**: Ask the user about their preferred tech stack. Suggest simple, modern defaults (e.g. JavaScript, Supabase, Vercel) but be smart and tailor your questions and suggestions based on their responses.
        3. Format the entire PRD in markdown.
        4. Do NOT output both a question and a PRD in the same response. If you need more info, only ask the next most important question.
        5. Never make up requirements—clarify with the user before adding details.
        6. Avoid scope creep and keep the PRD focused and actionable.

        Your output should be either:
        - A single clarifying question for the user, or
        - A complete PRD as markdown, following the above structure.
        """,
        agent=product_discovery_agent,
        expected_output="Either a single clarifying question for the user, or a complete prd.md file as markdown."
    )

def create_prd_improvement_task():
    # Always read the latest prd.md as input context
    prd_content = ''
    try:
        with open('prd.md', 'r') as f:
            prd_content = f.read()
    except Exception:
        prd_content = ''
    return Task(
        description=f"""
        Here is the current PRD (prd.md):
        ---
        {prd_content}
        ---
        Read and analyze the above PRD.

        Improve it by:
        - Ensuring clarity and removing redundancy
        - Verifying alignment with MVP best practices
        - Checking that scope is realistic and executable
        - Adding any missing critical information
        - Structuring content for maximum clarity

        Save the improved version as prd.md (overwrite the original).
        """,
        agent=prd_improvement_agent,
        expected_output="An improved, refined prd.md file"
    )

def create_task_breakdown_task():
    # Always read the latest prd.md as input context
    prd_content = ''
    try:
        with open('prd.md', 'r') as f:
            prd_content = f.read()
    except Exception:
        prd_content = ''
    return Task(
        description=f"""
        Using the following PRD (prd.md) as context:
        ---
        {prd_content}
        ---
        Write a granular, step-by-step plan to build the MVP described above.
        Each task must:
        - Be incredibly small and testable
        - Have a clear start and end
        - Focus on only one concern
        
        This plan will be handed off to an engineering LLM that will be instructed to complete one task at a time, allowing the user to test in between steps.
        
        Output the entire plan in a clear, numbered format. If needed, group related tasks by logical development phases (setup, DB, frontend, backend, deployment), but each task should remain atomic and focused.
        """,
        agent=task_breakdown_agent,
        expected_output="A comprehensive tasks.md file with all development tasks, each small, testable, and focused on one concern."
    )

def create_prompt_generator_task():
    # Always read the latest prd.md and tasks.md as input context
    prd_content = ''
    tasks_content = ''
    try:
        with open('prd.md', 'r') as f:
            prd_content = f.read()
    except Exception:
        prd_content = ''
    try:
        with open('tasks.md', 'r') as f:
            tasks_content = f.read()
    except Exception:
        tasks_content = ''
    return Task(
        description=f"""
        Build the best system prompt for an LLM you can. 
        You've been given two documents:
        - prd.md (PRD):
        ---
        {prd_content}
        ---
        - tasks.md:
        ---
        {tasks_content}
        ---
        Read both carefully. There should be no ambiguity about what we’re building.
        Follow tasks.md and complete one task at a time.
        After each task, stop. The user will test the result. If it works, commit to GitHub and move to the next task.

        ### CODING PROTOCOL ###
        Coding Instructions:
        - Write the absolute minimum code required
        - No sweeping changes
        - No unrelated edits – focus on just the task you're on
        - Make code precise, modular, testable
        - Don’t break existing functionality
        - If the user needs to do anything (e.g. Supabase/AWS config), tell them clearly

        Using this context, generate a markdown-formatted system prompt for the engineering LLM that will ensure it follows these instructions exactly.
        """,
        agent=prompt_generator_agent,
        expected_output="A complete prompt.md file to guide LLM execution, referencing both prd.md (prd.md) and tasks.md, and including the coding protocol. Make it comprehensive and the best prompt for MVP and product building."
    )

def run_crew(user_idea, mode="prd_only", prd_override=None):
    """
    mode: 'prd_only' runs only the Product Discovery Agent and returns PRD.
          'rest' runs the remaining agents, starting with an approved PRD.
    prd_override: If provided, use this PRD instead of generating a new one.
    """
    from crewai import Crew, Process
    if mode == "prd_only":
        # Only run Product Discovery Agent
        task1 = create_product_discovery_task(user_idea)
        crew = Crew(
            agents=[product_discovery_agent],
            tasks=[task1],
            process=Process.sequential,
            verbose=True
        )
        result = crew.kickoff()
        prd_content = result[0] if isinstance(result, list) and result else str(result)
        with open("prd.md", "w") as f:
            f.write(prd_content)
        return prd_content
    elif mode == "rest":
        if prd_override:
            with open("prd.md", "w") as f:
                f.write(prd_override)
        # Run PRD Improvement Agent
        task2 = create_prd_improvement_task()
        crew2 = Crew(
            agents=[prd_improvement_agent],
            tasks=[task2],
            process=Process.sequential,
            verbose=True
        )
        improved_prd = crew2.kickoff()
        improved_prd_content = improved_prd[0] if isinstance(improved_prd, list) and improved_prd else str(improved_prd)
        with open("prd.md", "w") as f:
            f.write(improved_prd_content)
        # Run Task Breakdown Agent
        task3 = create_task_breakdown_task()
        crew3 = Crew(
            agents=[task_breakdown_agent],
            tasks=[task3],
            process=Process.sequential,
            verbose=True
        )
        tasks_md = crew3.kickoff()
        tasks_md_content = tasks_md[0] if isinstance(tasks_md, list) and tasks_md else str(tasks_md)
        with open("tasks.md", "w") as f:
            f.write(tasks_md_content)
        # Run System Prompt Generator Agent
        task4 = create_prompt_generator_task()
        crew4 = Crew(
            agents=[prompt_generator_agent],
            tasks=[task4],
            process=Process.sequential,
            verbose=True
        )
        prompt_md = crew4.kickoff()
        prompt_md_content = prompt_md[0] if isinstance(prompt_md, list) and prompt_md else str(prompt_md)
        with open("prompt.md", "w") as f:
            f.write(prompt_md_content)
        return {
            'prd.md': improved_prd_content,
            'tasks.md': tasks_md_content,
            'prompt.md': prompt_md_content
        }
    else:
        raise ValueError("Invalid mode for run_crew")

if __name__ == "__main__":
    # Test run
    user_idea = "A simple todo app with user authentication"
    result = run_crew(user_idea)
    print("Crew execution completed!")
    print(result)
