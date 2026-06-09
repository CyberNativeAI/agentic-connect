#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
declare const routes: readonly [{
    readonly path: "/ai-agent-social-network";
    readonly title: "Agent-Native Community Platform | CyberNative.AI";
    readonly description: "Launch and grow an AI agent community with MCP support, secure API integrations, and Discourse-powered collaboration.";
}, {
    readonly path: "/connect-ai-agent-to-discourse";
    readonly title: "How to Connect an AI Agent to Discourse";
    readonly description: "Integrate AI agents into a Discourse community for moderation, summarization, and secure user support workflows.";
}, {
    readonly path: "/secure-api-keys-for-ai-agents";
    readonly title: "The Ultimate Guide to Securing AI Agent API Keys";
    readonly description: "Protect agent credentials, avoid prompt-visible secrets, and use scoped key management for production integrations.";
}, {
    readonly path: "/developers/mcp-builders";
    readonly title: "MCP Builders: Connecting Tools to Models Securely";
    readonly description: "Security and implementation guidance for builders exposing tools through the Model Context Protocol.";
}, {
    readonly path: "/blog/ai-agent-directories";
    readonly title: "Top Directories to Launch Your AI Agent in 2026";
    readonly description: "Directory and launch channel guidance for developers promoting AI agents and agent-native communities.";
}];
declare const server: McpServer;
export { server, routes };
