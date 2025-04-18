from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders.firecrawl import FireCrawlLoader
from agent.graph.models.embeddings import embeddings
from agent.graph.vector_stores import get_vector_store
from firecrawl import FireCrawlApp
from langchain_core.documents import Document
import os
load_dotenv()

urls1 = [

]

urls2 = [

]

urls3 = [
    "https://langchain-ai.github.io/langgraph/tutorials/introduction/",
    "https://langchain-ai.github.io/langgraph/tutorials/deployment/",
    "https://langchain-ai.github.io/langgraph/how-tos/state-reducers/",
    "https://langchain-ai.github.io/langgraph/how-tos/sequence/",
    "https://langchain-ai.github.io/langgraph/how-tos/branching/",
    "https://langchain-ai.github.io/langgraph/how-tos/recursion-limit/",
    "https://langchain-ai.github.io/langgraph/how-tos/visualization/",
    "https://langchain-ai.github.io/langgraph/how-tos/map-reduce/",
    "https://langchain-ai.github.io/langgraph/how-tos/command/",
    "https://langchain-ai.github.io/langgraph/how-tos/configuration/",
    "https://langchain-ai.github.io/langgraph/how-tos/node-retries/",
    "https://langchain-ai.github.io/langgraph/how-tos/return-when-recursion-limit-hits/",
    "https://langchain-ai.github.io/langgraph/how-tos/persistence/",
    "https://langchain-ai.github.io/langgraph/how-tos/subgraph-persistence/",
    "https://langchain-ai.github.io/langgraph/how-tos/cross-thread-persistence/",
    "https://langchain-ai.github.io/langgraph/how-tos/persistence_postgres/",
    "https://langchain-ai.github.io/langgraph/how-tos/persistence_mongodb/",
    "https://langchain-ai.github.io/langgraph/how-tos/persistence_redis/",
    "https://langchain-ai.github.io/langgraph/how-tos/persistence-functional/",
    "https://langchain-ai.github.io/langgraph/how-tos/cross-thread-persistence-functional/",
    "https://langchain-ai.github.io/langgraph/how-tos/memory/manage-conversation-history/",
    "https://langchain-ai.github.io/langgraph/how-tos/memory/delete-messages/",
    "https://langchain-ai.github.io/langgraph/how-tos/memory/add-summary-conversation-history/",
    "https://langchain-ai.github.io/langgraph/how-tos/memory/semantic-search/",
    "https://langchain-ai.github.io/langgraph/how-tos/memory/semantic-search/#using-in-create-react-agent",
    "https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/wait-user-input/",
    "https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/review-tool-calls/",
    "https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/breakpoints/",
    "https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/edit-graph-state/",
    "https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/dynamic_breakpoints/",
    "https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/time-travel/",
    "https://langchain-ai.github.io/langgraph/how-tos/wait-user-input-functional/",
    "https://langchain-ai.github.io/langgraph/how-tos/review-tool-calls-functional/",
    "https://langchain-ai.github.io/langgraph/how-tos/streaming/",
    "https://langchain-ai.github.io/langgraph/how-tos/streaming-tokens/",
    "https://langchain-ai.github.io/langgraph/how-tos/streaming-specific-nodes/",
    "https://langchain-ai.github.io/langgraph/how-tos/streaming-events-from-within-tools/",
    "https://langchain-ai.github.io/langgraph/how-tos/streaming-subgraphs/",
    "https://langchain-ai.github.io/langgraph/how-tos/disable-streaming/",
    "https://langchain-ai.github.io/langgraph/how-tos/tool-calling/",
    "https://langchain-ai.github.io/langgraph/how-tos/tool-calling-errors/",
    "https://langchain-ai.github.io/langgraph/how-tos/pass-run-time-values-to-tools/",
    "https://langchain-ai.github.io/langgraph/how-tos/pass-config-to-tools/",
    "https://langchain-ai.github.io/langgraph/how-tos/update-state-from-tools/",
    "https://langchain-ai.github.io/langgraph/how-tos/many-tools/",
    "https://langchain-ai.github.io/langgraph/how-tos/subgraph/",
    "https://langchain-ai.github.io/langgraph/how-tos/subgraphs-manage-state/",
    "https://langchain-ai.github.io/langgraph/how-tos/subgraph-transform-state/",
    "https://langchain-ai.github.io/langgraph/how-tos/agent-handoffs/",
    "https://langchain-ai.github.io/langgraph/how-tos/multi-agent-network/",
    "https://langchain-ai.github.io/langgraph/how-tos/multi-agent-network-functional/",
    "https://langchain-ai.github.io/langgraph/how-tos/multi-agent-multi-turn-convo/",
    "https://langchain-ai.github.io/langgraph/how-tos/multi-agent-multi-turn-convo-functional/",
    "https://langchain-ai.github.io/langgraph/how-tos/state-model/",
    "https://langchain-ai.github.io/langgraph/how-tos/input_output_schema/",
    "https://langchain-ai.github.io/langgraph/how-tos/pass_private_state/",
    "https://langchain-ai.github.io/langgraph/how-tos/async/",
    "https://langchain-ai.github.io/langgraph/how-tos/react-agent-structured-output/",
    "https://langchain-ai.github.io/langgraph/how-tos/run-id-langsmith/",
    "https://langchain-ai.github.io/langgraph/how-tos/autogen-integration/",
    "https://langchain-ai.github.io/langgraph/how-tos/autogen-langgraph-platform/",
    "https://langchain-ai.github.io/langgraph/how-tos/autogen-integration-functional/",
    "https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/",
    "https://langchain-ai.github.io/langgraph/how-tos/create-react-agent-memory/",
    "https://langchain-ai.github.io/langgraph/how-tos/create-react-agent-system-prompt/",
    "https://langchain-ai.github.io/langgraph/how-tos/create-react-agent-hitl/",
    "https://langchain-ai.github.io/langgraph/how-tos/create-react-agent-structured-output/",
    "https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch/",
    "https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch-functional/",
    "https://langchain-ai.github.io/langgraph/how-tos/deploy-self-hosted/",
    "https://langchain-ai.github.io/langgraph/how-tos/use-remote-graph/",
    "https://langchain-ai.github.io/langgraph/how-tos/auth/custom_auth/",
    "https://langchain-ai.github.io/langgraph/how-tos/auth/openapi_security/",
    "https://langchain-ai.github.io/langgraph/how-tos/http/custom_routes/",
    "https://langchain-ai.github.io/langgraph/how-tos/http/custom_middleware/",
    "https://langchain-ai.github.io/langgraph/how-tos/http/custom_lifespan/",
    "https://langchain-ai.github.io/langgraph/concepts/high_level/",
    "https://langchain-ai.github.io/langgraph/concepts/low_level/",
    "https://langchain-ai.github.io/langgraph/concepts/agentic_concepts/",
    "https://langchain-ai.github.io/langgraph/concepts/multi_agent/",
    "https://langchain-ai.github.io/langgraph/concepts/breakpoints/",
    "https://langchain-ai.github.io/langgraph/concepts/persistence/",
    "https://langchain-ai.github.io/langgraph/concepts/memory/",
    "https://langchain-ai.github.io/langgraph/concepts/time-travel/",
    "https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/",
    "https://langchain-ai.github.io/langgraph/concepts/functional_api/",
    "https://langchain-ai.github.io/langgraph/concepts/streaming/",
    "https://langchain-ai.github.io/langgraph/concepts/assistants/",
    "https://langchain-ai.github.io/langgraph/concepts/durable_execution/",
    "https://langchain-ai.github.io/langgraph/concepts/pregel/",
    "https://langchain-ai.github.io/langgraph/concepts/langgraph_platform/",
    "https://langchain-ai.github.io/langgraph/concepts/deployment_options/",
    "https://langchain-ai.github.io/langgraph/concepts/langgraph_cloud/",
    "https://langchain-ai.github.io/langgraph/concepts/bring_your_own_cloud/",
    "https://langchain-ai.github.io/langgraph/concepts/self_hosted/",
    "https://langchain-ai.github.io/langgraph/concepts/plans/",
    "https://langchain-ai.github.io/langgraph/concepts/template_applications/",
    "https://langchain-ai.github.io/langgraph/concepts/langgraph_server/",
    "https://langchain-ai.github.io/langgraph/concepts/langgraph_studio/",
    "https://langchain-ai.github.io/langgraph/concepts/langgraph_cli/",
    "https://langchain-ai.github.io/langgraph/concepts/sdk/",
    "https://langchain-ai.github.io/langgraph/concepts/application_structure/",
    "https://langchain-ai.github.io/langgraph/concepts/double_texting/",
    "https://langchain-ai.github.io/langgraph/concepts/auth/",
    "https://langchain-ai.github.io/langgraph/troubleshooting/errors/GRAPH_RECURSION_LIMIT/",
    "https://langchain-ai.github.io/langgraph/troubleshooting/errors/INVALID_CONCURRENT_GRAPH_UPDATE/",
    "https://langchain-ai.github.io/langgraph/troubleshooting/errors/INVALID_GRAPH_NODE_RETURN_VALUE/",
    "https://langchain-ai.github.io/langgraph/troubleshooting/errors/MULTIPLE_SUBGRAPHS/",
    "https://langchain-ai.github.io/langgraph/troubleshooting/errors/INVALID_CHAT_HISTORY/",
    "https://langchain-ai.github.io/langgraph/troubleshooting/errors/INVALID_LICENSE/",
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
    "https://langchain-ai.github.io/langgraph/cloud/reference/environment_variables/",
    "https://langchain-ai.github.io/langgraph/cloud/deployment/setup/",
    "https://langchain-ai.github.io/langgraph/cloud/deployment/setup_pyproject/",
    "https://langchain-ai.github.io/langgraph/cloud/deployment/setup_javascript/",
    "https://langchain-ai.github.io/langgraph/cloud/deployment/semantic_search/",
    "https://langchain-ai.github.io/langgraph/cloud/deployment/custom_docker/",
    "https://langchain-ai.github.io/langgraph/cloud/deployment/test_locally/",
    "https://langchain-ai.github.io/langgraph/cloud/deployment/graph_rebuild/",
    "https://langchain-ai.github.io/langgraph/cloud/deployment/cloud/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/configuration_cloud/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/assistant_versioning/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/copy_threads/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/check_thread_status/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/background_run/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/same-thread/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/cron_jobs/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/stateless_runs/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/stream_values/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/stream_updates/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/stream_messages/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/stream_events/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/stream_debug/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/stream_multiple/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/use_stream_react/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/generative_ui_react/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/human_in_the_loop_breakpoint/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/human_in_the_loop_user_input/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/human_in_the_loop_edit_state/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/human_in_the_loop_time_travel/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/human_in_the_loop_review_tool_calls/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/interrupt_concurrent/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/rollback_concurrent/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/reject_concurrent/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/enqueue_concurrent/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/webhooks/",
    "https://langchain-ai.github.io/langgraph/cloud/how-tos/cron_jobs/"
]

urls4 = [
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
    "https://docs.copilotkit.ai/reference/sdk/js/LangGraph",
    "https://docs.copilotkit.ai/reference/sdk/python/RemoteEndpoints",
    "https://docs.copilotkit.ai/reference/sdk/python/LangGraphAgent",
    "https://docs.copilotkit.ai/reference/sdk/python/LangGraph",
    "https://docs.copilotkit.ai/reference/sdk/python/CrewAIAgent",
    "https://docs.copilotkit.ai/reference/sdk/python/CrewAI",
    "https://docs.copilotkit.ai/coagents",
    "https://docs.copilotkit.ai/coagents/quickstart/langgraph",
    "https://docs.copilotkit.ai/coagents/agentic-chat-ui",
    "https://docs.copilotkit.ai/coagents/generative-ui",
    "https://docs.copilotkit.ai/coagents/generative-ui/agentic",
    "https://docs.copilotkit.ai/coagents/generative-ui/tool-based",
    "https://docs.copilotkit.ai/coagents/human-in-the-loop",
    "https://docs.copilotkit.ai/coagents/human-in-the-loop/interrupt-flow",
    "https://docs.copilotkit.ai/coagents/human-in-the-loop/node-flow",
    "https://docs.copilotkit.ai/coagents/shared-state",
    "https://docs.copilotkit.ai/coagents/shared-state/in-app-agent-read",
    "https://docs.copilotkit.ai/coagents/shared-state/in-app-agent-write",
    "https://docs.copilotkit.ai/coagents/shared-state/state-inputs-outputs",
    "https://docs.copilotkit.ai/coagents/shared-state/predictive-state-updates",
    "https://docs.copilotkit.ai/coagents/frontend-actions",
    "https://docs.copilotkit.ai/coagents/multi-agent-flows",
    "https://docs.copilotkit.ai/coagents/persistence/loading-agent-state",
    "https://docs.copilotkit.ai/coagents/persistence/loading-message-history",
    "https://docs.copilotkit.ai/coagents/persistence/message-persistence",
    "https://docs.copilotkit.ai/coagents/advanced/adding-runtime-configuration",
    "https://docs.copilotkit.ai/coagents/advanced/disabling-state-streaming",
    "https://docs.copilotkit.ai/coagents/advanced/emit-messages",
    "https://docs.copilotkit.ai/coagents/advanced/exit-agent",
    "https://docs.copilotkit.ai/quickstart",
    "https://docs.copilotkit.ai/guides",
    "https://docs.copilotkit.ai/guides/custom-look-and-feel",
    "https://docs.copilotkit.ai/guides/custom-look-and-feel/built-in-ui-components",
    "https://docs.copilotkit.ai/guides/custom-look-and-feel/customize-built-in-ui-components",
    "https://docs.copilotkit.ai/guides/custom-look-and-feel/bring-your-own-components",
    "https://docs.copilotkit.ai/guides/custom-look-and-feel/headless-ui",
    "https://docs.copilotkit.ai/guides/connect-your-data",
    "https://docs.copilotkit.ai/guides/connect-your-data/frontend",
    "https://docs.copilotkit.ai/guides/connect-your-data/backend",
    "https://docs.copilotkit.ai/guides/generative-ui",
    "https://docs.copilotkit.ai/guides/frontend-actions",
    "https://docs.copilotkit.ai/guides/backend-actions",
    "https://docs.copilotkit.ai/guides/backend-actions/typescript-backend-actions",
    "https://docs.copilotkit.ai/guides/backend-actions/langchain-js-backend-actions",
    "https://docs.copilotkit.ai/guides/backend-actions/langserve-backend-actions",
    "https://docs.copilotkit.ai/guides/backend-actions/remote-backend-endpoint",
    "https://docs.copilotkit.ai/guides/backend-actions/langgraph-platform-endpoint",
    "https://docs.copilotkit.ai/guides/custom-ai-assistant-behavior",
    "https://docs.copilotkit.ai/guides/authenticated-actions",
    "https://docs.copilotkit.ai/guides/guardrails",
    "https://docs.copilotkit.ai/guides/copilot-suggestions",
    "https://docs.copilotkit.ai/guides/bring-your-own-llm",
    "https://docs.copilotkit.ai/guides/copilot-textarea",
    "https://docs.copilotkit.ai/guides/self-hosting",
    "https://docs.copilotkit.ai/guides/messages-localstorage",
    "https://docs.copilotkit.ai/cookbook/state-machine",
    "https://docs.copilotkit.ai/troubleshooting/common-issues"
]

def ingest_documents(framework, docs_list):
    """Ingest documents into the vector store."""
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=600, chunk_overlap=50
    )
    doc_splits = text_splitter.split_documents(docs_list)

    if len(doc_splits) > 0:
        # Get the appropriate vector store based on environment
        vector_store = get_vector_store(framework, embeddings)
        
        if vector_store:
            # Add documents to the vector store
            print(f"Adding {len(doc_splits)} documents to vector store for {framework}")
            vector_store.add_documents(doc_splits)
            return True
        else:
            print(f"Error: Could not create vector store for {framework}")
            return False
    else:
        print("No documents to ingest")
        return False

for framework, urls in zip(
        ["openai", "smolagents", "langgraph", "copilotkit"], 
        [urls1, urls2, urls3, urls4]
    ):
    print(f"\nProcessing {framework} documentation...")
    docs_list = []
    
    app = FireCrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
    for url in urls:
        print(f"FireCrawling {url}")
        try:
            result = app.scrape_url(url, formats=["markdown"])
            if result:
                content = result["markdown"]
                docs_list.append(Document(page_content=content, metadata={"source": url}))
            
            print(f"Successfully loaded documents from {url}")
        except Exception as e:
            print(f"Error loading {url}: {e}")
    
    # Ingest documents for this framework
    if docs_list:
        if ingest_documents(framework, docs_list):
            print(f"Successfully ingested {len(docs_list)} documents for {framework}")
        else:
            print(f"Error: Could not ingest documents for {framework}")
    else:
        print(f"No documents found for {framework}")
    