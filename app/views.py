from django.shortcuts import redirect, render
from django.shortcuts import render,redirect
from django.contrib.auth.models import User
from .models import *
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse



# prompt
from langchain_core.prompts import ChatPromptTemplate

def create_dynamic_prompt(role, guidelines, example_queries,response_style,name,tackline):
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""
 your name is {name} ,{tackline}

Your Role:
{role}

Guidelines:
{guidelines}

Response Style:
{response_style}

Example Queries:
{example_queries}
"""),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    return prompt


# LLM 
import os
from dotenv import load_dotenv
load_dotenv()
from langchain.agents import create_openai_functions_agent
from langchain_openai.chat_models import ChatOpenAI
from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain_community.utilities import SerpAPIWrapper
from langchain_community.tools.google_search import GoogleSearchRun,GoogleSearchResults
from langchain_community.tools.google_serper import GoogleSerperResults,GoogleSerperRun
from langgraph.graph import END, Graph

serpapi_api_key = os.getenv("SERPAPI_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
google_cse_id = os.getenv("GOOGLE_CSE_ID")
google_api_key = os.getenv("GOOGLE_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"]="true"
langchain_api_key = os.getenv("LANGCHAIN_API_KEY")

name = """Jayanta"""
tackline = """
- an expert Generative AI.
"""
role_text = """
- Provide concise, accurate, and comprehensive insights tailored to individual user needs.
- Answer questions clearly, even if the query isn't fully specific.

"""

guidelines_text = """
- Always provide the latest and most accurate information available.
"""

example_queries_text = """
- "What is life?"
"""
response_style = """
- Use a professional yet approachable tone.
- Be concise but ensure completeness in your explanations.
- Prioritize user education and provide additional resources when necessary.
"""

def create_dynamic_prompt_from_data(prompt_data):
    prompt = ChatPromptTemplate.from_messages([
                ("system", f"""
        your name is {prompt_data['name']} {prompt_data['tagline']}

        Your Role:
        {prompt_data['role']}

        Guidelines:
        {prompt_data['guidelines']}

        Response Style:
        {prompt_data['response_style']}

        Example Queries:
        {prompt_data['example_queries']}
        """),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ])
    return prompt


def prompts(request):
    prompt_data = request.session.get('dynamic_prompt_data')
    if prompt_data:
        dynamic_prompt = create_dynamic_prompt_from_data(prompt_data)
        print(dynamic_prompt)
        return dynamic_prompt
    else:
        dynamic_prompt = create_dynamic_prompt(role_text, guidelines_text, example_queries_text,response_style,name,tackline)
        print(dynamic_prompt)
        return dynamic_prompt



def genrate(request, query_data, dynamic_prompt):
    llm = ChatOpenAI(model="gpt-4-turbo")

    google = GoogleSearchAPIWrapper()
    serp_result = SerpAPIWrapper()
    tools = [
        GoogleSearchRun(api_wrapper=google),
        GoogleSearchResults(api_wrapper=google),
        # GoogleSerperResults(api_wrapper=serp_result),
        # GoogleSerperRun(api_wrapper=serp_result),
    ]

    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.agents import AgentFinish

    agent_runnable = create_openai_functions_agent(llm, tools, dynamic_prompt)
    agent = RunnablePassthrough.assign(
        agent_outcome = agent_runnable
    )

    def execute_tools(data):
        agent_action = data.pop('agent_outcome')
        tool_to_use = {t.name: t for t in tools}[agent_action.tool]
        observation = tool_to_use.invoke(agent_action.tool_input)
        data['intermediate_steps'].append((agent_action, observation))
        return data

    def should_continue(data):
        if isinstance(data['agent_outcome'], AgentFinish):
            return "exit"
        else:
            return "continue"

    workflow = Graph()
    workflow.add_node("agent", agent)
    workflow.add_node("tools", execute_tools)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "tools",
            "exit": END
        }
    )
    workflow.add_edge('tools', 'agent')
    chain = workflow.compile()
    result = chain.invoke({"input": query_data, "intermediate_steps": []})
    output = result['agent_outcome'].return_values["output"]
    return output


# Create your views here.

def register(request):
    if request.method=='POST':
        uemail=request.POST.get('email')
        print(uemail)
        name=request.POST.get('name')
        country=request.POST.get('country')
       
        password=request.POST.get('pass')

        details = user_details(
                               name = name,
                               useremail = uemail,
                               country = country,
                               password = password)
        details.save()
        request.session['userid'] = details.id
        return redirect('profile-setup')

    return render(request,'register.html')

def login(request):
    if request.method=='POST':
        try:
            details = user_details.objects.get(useremail=request.POST.get('email'),password = request.POST.get('password'))

            request.session['userid'] = details.id
            return redirect('profile-setup')
        except:
            messages.error(request, 'Incorrect Password or Email-ID')
            return redirect('login')

    return render(request,'login.html')


def logout_user(request):
    logout(request)
    return redirect('login') 


def ai_chat(request):
    try:
        user = user_details.objects.get(id=request.session['userid'])
        print("user_id", user.id)
        if request.method == 'POST':
            message = request.POST.get('message')
            print(message)
            dynamic_prompt = prompts(request)  # Get the dynamic prompt
            print(dynamic_prompt)
            check = genrate(request, message, dynamic_prompt)  # Pass dynamic_prompt to genrate
            if check is not None:
                return JsonResponse({'message': message, 'response': check})
        return render(request, 'chatAI.html', {"user": user})

    except user_details.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('login')
    except Exception as e:
        print(f"Error: {e}")
        messages.error(request, 'An error occurred.')
        return redirect('login')



def profile_setup(request):
    if request.method=='POST':
        name=request.POST.get('name')
        date=request.POST.get('date')
        tagline=request.POST.get('tagline')
        descrip=request.POST.get('descrip')
        about=request.POST.get('about')
        greet=request.POST.get('greet')
        visible=request.POST.get('visible')

        request.session['profile'] = {
            'name': name,
            'tagline': tagline,
            'descrip': descrip,
            'about': about,
            'greet': greet,
        }
        
        role_text = f"""
        - Provide concise, accurate, and comprehensive insights tailored to individual user needs.
        - Answer questions clearly, even if the query isn't fully specific.
        {about},{descrip}
        """
        name = f"""{name}"""

        tagline = f"""
        {tagline}
        """
        guidelines_text = f"""
        - Always provide the latest and most accurate information available.
        {greet}
        """
        example_queries_text = """
        - "What is life?"
        """
        response_style = """
        - Use a professional yet approachable tone.
        - Be concise but ensure completeness in your explanations.
        - Prioritize user education and provide additional resources when necessary.
        """
        prompt_data = {
            'role': role_text,
            'guidelines': guidelines_text,
            'example_queries': example_queries_text,
            'response_style': response_style,
            'name': name,
            'tagline': tagline
        }
        request.session['dynamic_prompt_data'] = prompt_data
        return redirect('chat')
    return render(request,'profile.html')