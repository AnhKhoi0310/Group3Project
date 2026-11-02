# AI-Assisted Development and Review Context Document

This document outlines our team's guidelines for using AI-assisted coding tools, including code review, testing, security, and documentation. The goal is to ensure AI-generated code is reliable, secure, and properly reviewed before merging.

1. AI Coding Tools
    Our team plans to use AI assisted coding tools such as Anthropic Claude to support development. These tools may be used for generating code, debugging, refactoring, writing tests, and explaining technical concepts and must be reviewed before being merged into the project.

2. Context Provided to AI Tools
    Previous information given will be used for context for AI integration. Context includes:
    + Frontend: React, TypeScript, and Tailwind CSS
    + Backend: Python and FastAPI
    + Databases: MySQL and MongoDB
    + Authentication: Firebase Authentication
    + Deployment: AWS
    Prompts should also explain the feature being developed, expected behavior, relevant data structures, and existing coding conventions. Sensitive information such as API keys, passwords, and authentication tokens must not be included in prompts.

3. Reviewing AI Generated Code 
    All AI generated code must be reviewed by a developer before it is accepted. The review should verify that the code correctly implements the requested functionality. It should also follow the project's architecture and be readable, maintainable, and does not introduce unnecessary complexity or security vulnerabilities. Responsibility for understanding AI generated code rather than copying it directly into the project without verification is required.

4. Validating Generated Dependencies and APIs
    AI tools may suggest outdated libraries, incorrect methods, or APIs that do not exist.
    Before using AI generated dependencies or API integrations, developers must:
    + Verify packages through official documentation or trusted package registries. 
    + Check compatibility with the project's existing technologies.Review dependencies for known security vulnerabilities. 
    + Confirm that generated API calls use valid endpoints, parameters, and authentication methods. 
    + Avoid adding unnecessary dependencies. 
    This is especially important for integrations involving Firebase Authentication, Anthropic Claude, MySQL, MongoDB, and AWS.

5. Required Testing
    AI-generated code must meet the same testing standards as code written manually. Before acceptance, developers must verify that individual functions and components work correctly, confirm that frontend, backend, database, and external services interact correctly, check how the application handles invalid or unexpected inputs, including CSV and JSON uploads, andverify authentication, authorization, and protection of sensitive data. These features should work as expected. All required automated tests and code quality checks must pass before the code can be merged.

6. AI Session Transcript Retention
    For significant AI assisted development tasks, the team will retain records of AI interactions for transparency and future reference. *Relevant prompts, responses, and important implementation decisions should be saved in a shared, access-controlled project location.* Each major record should the prompt, the date, and any important changes made to the generated code. Sensitive information must be removed before storing transcripts. Routine autocomplete suggestions do not require individual records.

7. Additional Security Review
    + Database operations: Access to customer reviews, user information, and organization data
    + File uploads: Processing CSV/JSON files and preventing malicious input
    + AI integration: Sending customer reviews to Claude, handling AI responses, and preventing prompt injection
    + Infrastructure: AWS configurations, environment variables, API keys, and deployment permissions
    + Changes must be reviewed by another qualified team member to ensure they meet the project's security requirements

Our team will use AI coding tools to improve development efficiency while maintaining code quality and security. All AI-generated code must be reviewed, validated, and tested before merging. Developers remain responsible for the correctness and security of any code produced with AI assistance.