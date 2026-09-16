## Purpose

Orchestrates dynamic, request-scoped tool binding to the agent runtime with opt-in activation, concurrent execution, and resilient error handling.

## ADDED Requirements

### Requirement: Request-Level Opt-In Tool Binding
The agent runtime SHALL only bind tools that are explicitly requested in the execution request, enabling zero tools by default.

#### Scenario: Request without tool parameter
- **WHEN** a client calls `POST /stream` with no `tools` parameter or an empty `tools` list
- **THEN** the agent SHALL run with zero tools bound and generate a direct conversational response without tool invocation

#### Scenario: Request with valid tool whitelist
- **WHEN** a client calls `POST /stream` specifying `tools: ["get_weather_forecast"]`
- **THEN** only the `get_weather_forecast` tool SHALL be bound to the LLM for that run

#### Scenario: Request with unknown tool name
- **WHEN** a client calls `POST /stream` with an unrecognized tool name in the `tools` list
- **THEN** the system SHALL reject the request with an HTTP 400 error indicating the invalid tool name

### Requirement: Concurrent Tool Execution
When the agent decides to invoke multiple tool calls in a single turn, the system SHALL execute them concurrently.

#### Scenario: Multiple simultaneous tool calls
- **WHEN** the LLM generates multiple tool calls in a single step
- **THEN** the tool execution node SHALL invoke all requested tools concurrently and collect their results before returning to the model

### Requirement: Resilient Tool Error Handling
Tool execution failures, timeouts, or exceptions SHALL be captured and returned to the model as error messages without crashing the stream.

#### Scenario: Tool raises an unhandled exception
- **WHEN** a tool raises an unhandled exception during execution
- **THEN** the execution node SHALL capture the error and return a ToolMessage describing the failure, allowing the agent to formulate an informative response
