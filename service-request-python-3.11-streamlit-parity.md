# Service Request: Install Python 3.11 on Self-Hosted Azure DevOps Agent (Streamlit Container Runtime Parity)

| Field | Detail |
|---|---|
| **Request Type** | Infrastructure / Build Agent Configuration |
| **Priority** | Low-Medium — not blocking current deployments |
| **Requested By** | *[Your name]* |
| **Team** | *[Your team / project]* |
| **Target System** | Self-hosted Azure DevOps build agent(s) |
| **Agent Pool** | *[Agent pool name — fill in]* |
| **Requested Completion** | *[Date]* |

## Summary

We're requesting Python 3.11.x be added to the self-hosted agent(s) in **[agent pool name]**, registered in the agent's tool cache so it's selectable via the `UsePythonVersion@0` pipeline task (alongside the existing 3.8.10 and 3.9.5).

## Technical Background

Per Snowflake's documentation on Streamlit in Snowflake:

> For container runtimes, Python 3.11 is the only currently supported version.

**Important context on scope:** this requirement applies to the Python version that Snowflake itself uses to *run* our container-runtime Streamlit apps — it is a property of the Snowflake-managed runtime, not of our build agent. Our CI/CD pipeline's deploy step (Snowflake CLI, installed via standalone `.deb` binary) is already fully decoupled from the agent's Python version and works correctly on the existing Python 3.9.5. **This request is not required for the pipeline to function.**

## Business Justification

We're requesting Python 3.11 on the agent for **local development and testing parity**, not deployment:
- We'd like the ability to run/smoke-test Streamlit app code directly on the agent (or in a dev/test pipeline stage) using the same Python version (3.11) that Snowflake will actually execute it on in production, for both container-runtime and default warehouse-runtime apps.
- This reduces the risk of "works locally, breaks in Snowflake" issues caused by Python version drift between our test environment and Snowflake's managed runtime.
- Consistency with local developer machines, which use 3.11.

## What We're Asking For

Please install Python 3.11.x on the agent(s) such that it is discoverable by the `UsePythonVersion@0` pipeline task — i.e. registered in the agent's tool cache (`$(Agent.ToolsDirectory)`, typically `_work/_tool`) alongside the existing versions, per Microsoft's guide on [configuring side-by-side Python versions on self-hosted agents](https://go.microsoft.com/fwlink/?linkid=871498).

### Specifics
- **Version:** Python 3.11.x (latest patch release is fine)
- **Architecture:** x64
- **Agent(s) affected:** *[list specific agent names/pool, or "all agents in pool X"]*
- **Install location:** Registered in the agent's tool cache (not just a system-wide binary) so it's selectable via `versionSpec: '3.11'`

## Acceptance Criteria

- [ ] Python 3.11.x installed and registered in the agent's tool cache
- [ ] A test pipeline step with `versionSpec: '3.11'` succeeds without the `did not match any version in Agent.ToolsDirectory` error
- [ ] Existing 3.8.10 and 3.9.5 installs remain untouched and functional
- [ ] Existing Snowflake CLI deploy step (uses `.deb` binary, not Python) continues to work unaffected

## Non-Goals

To avoid any ambiguity for the reviewer: this request does **not** change or affect our production deployment pipeline in any way. It is solely to support local/agent-side testing on a Python version matching Snowflake's Streamlit runtime.

## Contact

For questions about this request, contact *[your name / team channel]*.
