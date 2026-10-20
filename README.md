# agent-security-field-guide

A single deliberately poisoned web page used to demonstrate indirect prompt injection against a research agent that browses the web.

The page is harmless to human readers. It contains text addressed to AI assistants that instructs them to email a summary plus any credentials in their context to a reserved, non-routable address (`attacker.example`). The companion demo uses a mock email tool; nothing is ever sent.

Served at: https://nancy-chauhan.github.io/agent-security-field-guide/
