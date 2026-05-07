"""
Agentic Layer - LLM integration for dynamic tool selection and execution
"""

from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime
from enum import Enum
import asyncio
import json
import logging
from pydantic import BaseModel, Field
from tools.registry.tool_registry import ToolRegistry, ToolDefinition, ToolExecutionRequest
from workflows.engine.workflow_engine import WorkflowEngine, WorkflowDefinition

logger = logging.getLogger(__name__)

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    LOCAL = "local"

class AgentCapability(str, Enum):
    TOOL_SELECTION = "tool_selection"
    WORKFLOW_GENERATION = "workflow_generation"
    NATURAL_LANGUAGE_EXECUTION = "natural_language_execution"
    REASONING = "reasoning"
    PLANNING = "planning"

class AgentRequest(BaseModel):
    """Request to the agentic layer"""
    user_id: str
    prompt: str
    context: Dict[str, Any] = {}
    capabilities: List[AgentCapability] = []
    available_tools: List[str] = []
    constraints: Dict[str, Any] = {}
    session_id: Optional[str] = None

class AgentResponse(BaseModel):
    """Response from the agentic layer"""
    success: bool
    response: str
    tool_calls: List[Dict[str, Any]] = []
    workflow_suggestion: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = {}

class ToolCall(BaseModel):
    """Tool call definition"""
    tool_id: str
    parameters: Dict[str, Any]
    reasoning: Optional[str] = None

class WorkflowSuggestion(BaseModel):
    """Suggested workflow"""
    name: str
    description: str
    steps: List[Dict[str, Any]]
    triggers: List[Dict[str, Any]] = []

class LLMClient:
    """Base class for LLM clients"""
    
    def __init__(self, provider: LLMProvider, config: Dict[str, Any]):
        self.provider = provider
        self.config = config
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """Make a chat completion request"""
        raise NotImplementedError
    
    async def function_calling(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Make a function calling request"""
        raise NotImplementedError

class OpenAIClient(LLMClient):
    """OpenAI API client"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(LLMProvider.OPENAI, config)
        self.api_key = config.get("api_key")
        self.model = config.get("model", "gpt-4")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """OpenAI chat completion"""
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error: {response.status} - {error_text}")
        
        except Exception as e:
            logger.error(f"OpenAI API request failed: {str(e)}")
            raise
    
    async def function_calling(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """OpenAI function calling"""
        # Convert functions to tools format
        tools = [{
            "type": "function",
            "function": func
        } for func in functions]
        
        return await self.chat_completion(messages, tools, temperature)

class AnthropicClient(LLMClient):
    """Anthropic Claude client"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(LLMProvider.ANTHROPIC, config)
        self.api_key = config.get("api_key")
        self.model = config.get("model", "claude-3-sonnet-20240229")
        self.base_url = config.get("base_url", "https://api.anthropic.com")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """Anthropic chat completion"""
        import aiohttp
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Convert messages to Claude format
        system_message = ""
        user_messages = []
        
        for message in messages:
            if message["role"] == "system":
                system_message = message["content"]
            else:
                user_messages.append(message)
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages
        }
        
        if system_message:
            payload["system"] = system_message
        
        if tools:
            payload["tools"] = tools
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/messages",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Anthropic API error: {response.status} - {error_text}")
        
        except Exception as e:
            logger.error(f"Anthropic API request failed: {str(e)}")
            raise

class AgenticLayer:
    """Main agentic layer for LLM integration"""
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        workflow_engine: WorkflowEngine,
        llm_config: Dict[str, Any] = None
    ):
        self.tool_registry = tool_registry
        self.workflow_engine = workflow_engine
        self.llm_client: Optional[LLMClient] = None
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        if llm_config:
            self._initialize_llm_client(llm_config)
    
    def _initialize_llm_client(self, config: Dict[str, Any]):
        """Initialize LLM client based on configuration"""
        provider = LLMProvider(config.get("provider", "openai"))
        
        if provider == LLMProvider.OPENAI:
            self.llm_client = OpenAIClient(config)
        elif provider == LLMProvider.ANTHROPIC:
            self.llm_client = AnthropicClient(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """Process an agentic request"""
        if not self.llm_client:
            return AgentResponse(
                success=False,
                response="LLM client not configured",
                confidence=0.0
            )
        
        try:
            # Get available tools
            available_tools = self._get_available_tools(request.available_tools)
            
            # Build system prompt
            system_prompt = self._build_system_prompt(request.capabilities, available_tools)
            
            # Build messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.prompt}
            ]
            
            # Add context if provided
            if request.context:
                context_message = f"Context: {json.dumps(request.context, indent=2)}"
                messages.insert(-1, {"role": "user", "content": context_message})
            
            # Prepare tools for LLM
            llm_tools = self._prepare_tools_for_llm(available_tools)
            
            # Make LLM request
            llm_response = await self.llm_client.chat_completion(
                messages=messages,
                tools=llm_tools if llm_tools else None,
                temperature=0.3
            )
            
            # Parse response
            return self._parse_llm_response(llm_response, request)
            
        except Exception as e:
            logger.error(f"Agentic request failed: {str(e)}")
            return AgentResponse(
                success=False,
                response=f"Processing failed: {str(e)}",
                confidence=0.0
            )
    
    async def execute_tool_calls(
        self,
        tool_calls: List[ToolCall],
        user_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute a list of tool calls"""
        results = []
        
        for tool_call in tool_calls:
            try:
                # Create execution request
                execution_request = ToolExecutionRequest(
                    tool_id=tool_call.tool_id,
                    parameters=tool_call.parameters,
                    user_context=user_context
                )
                
                # Execute tool
                result = await self.tool_registry.executor.execute(execution_request)
                
                results.append({
                    "tool_id": tool_call.tool_id,
                    "success": result.success,
                    "result": result.result,
                    "error": result.error,
                    "execution_time": result.execution_time
                })
                
            except Exception as e:
                results.append({
                    "tool_id": tool_call.tool_id,
                    "success": False,
                    "error": str(e),
                    "execution_time": 0.0
                })
        
        return results
    
    async def generate_workflow_from_prompt(
        self,
        prompt: str,
        user_context: Dict[str, Any] = None
    ) -> WorkflowSuggestion:
        """Generate a workflow from natural language prompt"""
        if not self.llm_client:
            raise RuntimeError("LLM client not configured")
        
        system_prompt = """
        You are a workflow generation expert. Given a user's request, generate a workflow 
        that accomplishes their goal using available tools and connectors.
        
        Return a JSON response with:
        - name: Workflow name
        - description: Workflow description  
        - steps: List of workflow steps with dependencies
        - triggers: List of triggers that should start the workflow
        
        Each step should include:
        - id: Unique step identifier
        - name: Step name
        - type: Step type (action, condition, delay, etc.)
        - config: Step configuration including tool_id and parameters
        - depends_on: List of step IDs this step depends on
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate a workflow for: {prompt}"}
        ]
        
        # Add available tools info
        available_tools = self._get_available_tools()
        tools_info = "\n".join([
            f"- {tool.name}: {tool.description}" 
            for tool in available_tools[:20]  # Limit to avoid token limits
        ])
        
        messages[1]["content"] += f"\n\nAvailable tools:\n{tools_info}"
        
        try:
            response = await self.llm_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
            # Extract workflow suggestion from response
            content = response["choices"][0]["message"]["content"]
            
            # Try to parse JSON from the response
            try:
                workflow_data = json.loads(content)
                return WorkflowSuggestion(**workflow_data)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from text
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    workflow_data = json.loads(json_match.group())
                    return WorkflowSuggestion(**workflow_data)
                else:
                    raise ValueError("Could not extract workflow JSON from response")
        
        except Exception as e:
            logger.error(f"Workflow generation failed: {str(e)}")
            raise
    
    async def create_and_execute_workflow(
        self,
        prompt: str,
        user_context: Dict[str, Any] = None
    ) -> str:
        """Create and execute a workflow from prompt"""
        # Generate workflow
        workflow_suggestion = await self.generate_workflow_from_prompt(prompt, user_context)
        
        # Convert to workflow definition
        workflow_def = WorkflowDefinition(
            name=workflow_suggestion.name,
            description=workflow_suggestion.description,
            steps=[
                {
                    "id": step["id"],
                    "name": step["name"],
                    "type": step["type"],
                    "config": step["config"],
                    "depends_on": step.get("depends_on", [])
                }
                for step in workflow_suggestion.steps
            ],
            trigger=workflow_suggestion.triggers[0] if workflow_suggestion.triggers else {}
        )
        
        # Register and execute workflow
        workflow_id = self.workflow_engine.register_workflow(workflow_def)
        execution_id = await self.workflow_engine.execute_workflow(
            workflow_id,
            trigger_data={"prompt": prompt},
            context=user_context or {}
        )
        
        return execution_id
    
    def _get_available_tools(self, tool_ids: List[str] = None) -> List[ToolDefinition]:
        """Get available tools"""
        if tool_ids:
            tools = []
            for tool_id in tool_ids:
                tool = self.tool_registry.get_tool(tool_id)
                if tool:
                    tools.append(tool)
            return tools
        else:
            return self.tool_registry.list_tools(status="active")
    
    def _build_system_prompt(
        self,
        capabilities: List[AgentCapability],
        available_tools: List[ToolDefinition]
    ) -> str:
        """Build system prompt for the LLM"""
        base_prompt = """
        You are an AI assistant that helps users accomplish tasks by selecting and executing tools.
        You have access to various tools and can help users create workflows.
        
        Be helpful, accurate, and explain your reasoning when making tool selections.
        Always verify that tool parameters are valid before making calls.
        """
        
        if AgentCapability.TOOL_SELECTION in capabilities:
            base_prompt += "\n\nYou can select and execute tools to help users accomplish their goals."
        
        if AgentCapability.WORKFLOW_GENERATION in capabilities:
            base_prompt += "\n\nYou can generate workflows by combining multiple tools in sequence."
        
        if AgentCapability.NATURAL_LANGUAGE_EXECUTION in capabilities:
            base_prompt += "\n\nYou can understand natural language requests and convert them to tool calls."
        
        if AgentCapability.REASONING in capabilities:
            base_prompt += "\n\nAlways explain your reasoning when selecting tools or generating workflows."
        
        if AgentCapability.PLANNING in capabilities:
            base_prompt += "\n\nBreak down complex tasks into smaller, manageable steps."
        
        return base_prompt
    
    def _prepare_tools_for_llm(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        """Prepare tools for LLM function calling"""
        llm_tools = []
        
        for tool in tools:
            tool_schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            # Add parameters
            for param in tool.parameters:
                tool_schema["function"]["parameters"]["properties"][param.name] = {
                    "type": param.type,
                    "description": param.description
                }
                
                if param.required:
                    tool_schema["function"]["parameters"]["required"].append(param.name)
                
                if param.enum:
                    tool_schema["function"]["parameters"]["properties"][param.name]["enum"] = param.enum
            
            llm_tools.append(tool_schema)
        
        return llm_tools
    
    def _parse_llm_response(
        self,
        llm_response: Dict[str, Any],
        request: AgentRequest
    ) -> AgentResponse:
        """Parse LLM response and extract tool calls"""
        try:
            message = llm_response["choices"][0]["message"]
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])
            
            # Extract tool calls
            parsed_tool_calls = []
            if tool_calls:
                for tool_call in tool_calls:
                    function = tool_call.get("function", {})
                    tool_name = function.get("name")
                    parameters = json.loads(function.get("arguments", "{}"))
                    
                    # Find tool ID by name
                    tool_id = None
                    for tool in self._get_available_tools(request.available_tools):
                        if tool.name == tool_name:
                            tool_id = tool.id
                            break
                    
                    if tool_id:
                        parsed_tool_calls.append(ToolCall(
                            tool_id=tool_id,
                            parameters=parameters
                        ))
            
            # Calculate confidence based on response
            confidence = 0.8  # Default confidence
            
            if tool_calls:
                confidence = 0.9  # Higher confidence with tool calls
            
            return AgentResponse(
                success=True,
                response=content,
                tool_calls=[tc.dict() for tc in parsed_tool_calls],
                confidence=confidence,
                metadata={
                    "model": llm_response.get("model"),
                    "usage": llm_response.get("usage", {}),
                    "finish_reason": message.get("finish_reason")
                }
            )
        
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return AgentResponse(
                success=False,
                response="Failed to process LLM response",
                confidence=0.0
            )
    
    def create_session(self, user_id: str) -> str:
        """Create a new agent session"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "messages": [],
            "context": {}
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, updates: Dict[str, Any]):
        """Update session"""
        if session_id in self.sessions:
            self.sessions[session_id].update(updates)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

# Global agentic layer instance
agentic_layer = AgenticLayer(
    tool_registry=None,  # Will be set during initialization
    workflow_engine=None,  # Will be set during initialization
    llm_config={
        "provider": "openai",
        "api_key": "your-api-key-here",
        "model": "gpt-4"
    }
)
