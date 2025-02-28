from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
from graph.models.embeddings import embeddings

load_dotenv()

urls1 = [
    "https://langchain-ai.github.io/langgraph/reference/graphs/",
    "https://langchain-ai.github.io/langgraph/reference/checkpointing/",
    "https://langchain-ai.github.io/langgraph/reference/store/",
    "https://langchain-ai.github.io/langgraph/reference/prebuilt/",
    "https://langchain-ai.github.io/langgraph/reference/channels/",
    "https://langchain-ai.github.io/langgraph/reference/errors/",
    "https://langchain-ai.github.io/langgraph/reference/types/",
    "https://langchain-ai.github.io/langgraph/reference/constants/",
    "https://langchain-ai.github.io/langgraph/reference/pregel/",
    "https://langchain-ai.github.io/langgraph/reference/config/",
    "https://langchain-ai.github.io/langgraph/reference/func/"
    "https://langchain-ai.github.io/langgraph/reference/functional/",
    "https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref/",
    "https://langchain-ai.github.io/langgraph/cloud/reference/sdk/python_sdk_ref/",
    "https://langchain-ai.github.io/langgraph/cloud/reference/sdk/js_ts_sdk_ref/",
    "https://langchain-ai.github.io/langgraph/cloud/reference/cli/",
    "https://langchain-ai.github.io/langgraph/cloud/reference/remote_graph/",
    "https://langchain-ai.github.io/langgraph/cloud/reference/environment_variables/"
]

urls2 = [

]

urls3 = [
    "https://docs.copilotkit.ai/reference/components/chat/CopilotChat",
    "https://docs.copilotkit.ai/reference/components/chat/CopilotPopup",
    "https://docs.copilotkit.ai/reference/components/chat/CopilotSidebar",
    "https://docs.copilotkit.ai/reference/components/CopilotTextarea",
    "https://docs.copilotkit.ai/reference/components/CopilotKit",
    "https://docs.copilotkit.ai/reference/hooks/useCopilotReadable",
    "https://docs.copilotkit.ai/reference/hooks/useCopilotAction",
    "https://docs.copilotkit.ai/reference/hooks/useCopilotAdditionalInstructions",
    "https://docs.copilotkit.ai/reference/hooks/useCopilotChat",
    "https://docs.copilotkit.ai/reference/hooks/useCopilotChatSuggestions",
    "https://docs.copilotkit.ai/reference/hooks/useCoAgent",
    "https://docs.copilotkit.ai/reference/hooks/useCoAgentStateRender",
    "https://docs.copilotkit.ai/reference/hooks/useLangGraphInterrupt"
    "https://docs.copilotkit.ai/reference/classes/CopilotTask",
    "https://docs.copilotkit.ai/reference/classes/CopilotRuntime",
    "https://docs.copilotkit.ai/reference/classes/llm-adapters/OpenAIAdapter",
    "https://docs.copilotkit.ai/reference/classes/llm-adapters/OpenAIAssistantAdapter",
    "https://docs.copilotkit.ai/reference/classes/llm-adapters/AnthropicAdapter",
    "https://docs.copilotkit.ai/reference/classes/llm-adapters/LangChainAdapter",
    "https://docs.copilotkit.ai/reference/classes/llm-adapters/GroqAdapter",
    "https://docs.copilotkit.ai/reference/classes/llm-adapters/GoogleGenerativeAIAdapter",
    "https://docs.copilotkit.ai/reference/sdk/python/RemoteEndpoints",
    "https://docs.copilotkit.ai/reference/sdk/python/LangGraphAgent",
    "https://docs.copilotkit.ai/reference/sdk/python/LangGraph",
    "https://docs.copilotkit.ai/reference/sdk/js/LangGraph",
    "https://docs.copilotkit.ai/guides/custom-look-and-feel/customize-built-in-ui-components",
    "https://docs.copilotkit.ai/guides/generative-ui",
    "https://docs.copilotkit.ai/guides/bring-your-own-llm",
    "https://docs.copilotkit.ai/coagents/quickstart/langgraph",
    "https://docs.copilotkit.ai/coagents/human-in-the-loop",
    "https://docs.copilotkit.ai/coagents/shared-state",
    "https://docs.copilotkit.ai/coagents/multi-agent-flows",
    "https://docs.copilotkit.ai/coagents"
]

for framework, urls in zip([],[urls1, urls2, urls3]):
    docs = [WebBaseLoader(url).load() for url in urls]
    docs_list = [item for sublist in docs for item in sublist]

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=600, chunk_overlap=50
    )
    doc_splits = text_splitter.split_documents(docs_list)

    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name="f{framework}",
        embedding=embeddings,
        persist_directory="./.chroma",
    )