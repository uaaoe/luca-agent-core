# Tool Registry Specification

## Purpose

Provides a modular tool registration and auto-discovery engine that exposes available tools and their parameter schemas through a REST discovery endpoint.

## Requirements

### Requirement: Automatic Tool Discovery
The system SHALL discover and import all Python tool modules located in the `app/tools/` directory during application startup.

#### Scenario: Module placed in tools directory
- **WHEN** a Python file defining tools is added to `app/tools/` and the application starts
- **THEN** the module SHALL be imported and its registered tools SHALL be available in the registry

#### Scenario: Non-Python or private files ignored
- **WHEN** files like `__pycache__` or non-python files exist in `app/tools/`
- **THEN** the discovery engine SHALL ignore them without raising errors

### Requirement: Tool Registry Introspection
The system SHALL maintain a central registry storing tool metadata including tool name, description, and parameter JSON schemas.

#### Scenario: Introspecting registered tool schema
- **WHEN** a tool is registered in the registry
- **THEN** the registry SHALL generate an accurate JSON Schema describing the tool's input parameters

### Requirement: Tools Discovery Endpoint
The system SHALL expose a `GET /tools` REST endpoint returning the catalog of all registered tools and their input schemas.

#### Scenario: Client queries available tools
- **WHEN** a client performs a `GET` request to `/tools`
- **THEN** the system SHALL return HTTP 200 with a JSON array listing all registered tools with their names, descriptions, and parameter schemas
