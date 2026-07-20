# MCP Server Trust Boundary

## Security Considerations

When the MCP server is implemented (Phase 4), it will expose Arian's context generation as a tool.

### Trust Boundaries

1. **Input validation**: All tool inputs must be validated through `ContextRequestValidator`
2. **Path restrictions**: MCP tool must only access configured repository roots
3. **Output sanitization**: MCP responses must go through `redact_secrets()`
4. **Rate limiting**: Implement rate limiting for MCP tool calls
5. **Authentication**: MCP server should require authentication for production use

### Implementation Notes

- Use `EnvironmentSecretProvider` for API keys
- Never log secrets or API keys
- All MCP tool calls should be logged with `run_id` for audit trail
- Consider implementing a `MCPSecurityPolicy` class that wraps the Application layer
