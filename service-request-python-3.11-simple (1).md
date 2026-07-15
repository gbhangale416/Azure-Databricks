# Service Request: Install Python 3.11 on Self-Hosted Azure DevOps Agent

**Requested By:** *[Your name]*
**Team:** *[Your team / project]*
**Agent Pool:** *[Agent pool name]*

## Request

We are setting up a new CI/CD pipeline to deploy the Snowflake Streamlit app to Snowflake.

For container runtimes, Python 3.11 is the only currently supported version.

Please install Python 3.11.x on the self-hosted agent(s) in **[agent pool name]**, registered in the agent's tool cache so it's available to the `UsePythonVersion@0` pipeline task (alongside the existing Python 3.8.10 and 3.9.5).

## Acceptance Criteria

- [ ] Python 3.11.x installed and available in the agent's tool cache
- [ ] Existing Python versions (3.8.10, 3.9.5) remain unaffected

## Contact

*[Your name / team channel]*
