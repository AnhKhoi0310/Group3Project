# Engineering Coding Standards

## Overview
This document sets the official coding standards for **Group3Project**. Every team member and AI coding tool must follow these rules when writing or updating code.

## 1. Repository and Folder Organization

Keep files in their specific locations so everyone knows where to find code:
```text
├── frontend/                 # User Interface (React + TypeScript + Tailwind CSS)
│   ├── src/
│   │   ├── components/       # Reusable UI pieces (buttons, cards, modals)
│   │   ├── pages/            # Screen views (Dashboard, Inbox, Settings)
│   │   ├── hooks/            # Shared React logic
│   │   ├── services/         # API calls to the backend
│   │   ├── types/            # TypeScript data definitions
│   │   └── utils/            # General helper tools
├── backend/                  # Server & Logic (FastAPI in Python)
│   ├── app/
│   ├── api/                  # API endpoints and routes
│   │   ├── models/           # Data shapes (Pydantic models / MongoDB & MySQL models)
│   │   ├── services/         # Core business logic (Claude AI prompts, CSV processing)
│   │   ├── db/               # Database setup and connections
│   │   └── core/             # Auth, settings, and general configurations
│   ├── tests/                # Test suite (Pytest)
│   └── main.py               # Entry point to run the server
└── docs/                     # Project documentation
```
## 2. Naming conventions
**Frontend(TypeScript / React / Tailwind CSS):**   
-  **Files & Folders:**   
     *  Use PascalCase(Ex. UserEmailAddress) for React components, use camelCase(Ex. shoppingCart) for utilities, hooks, and service files.


-  **Variables & Functions:**  
     *  Use camelCase(Ex. shoppingCart).


- **React Components:**  
  *  Use PascalCase(Ex. UserEmailAddress).


- **Types / Interfaces:**  
  *  Use PascalCase(Ex. UserEmailAddress).

- **Styles & CSS (Tailwind):**
  *   Apply Tailwind utility classes directly inside React components and for any custom CSS classes, use kebab-case(Ex. user-email-address).


**Backend(Python/FastAPI):**  
- **Files & Modules:**  
    *  Use snake_case(Ex. user_email_address).


-  **Variables & Functions:**  
    *  Use snake_case(Ex. user_email_address).


-  **Classes & Models:**
      *  Use PascalCase(Ex. UserEmailAddress).


-  **Constants:**  
    *  Use UPPER_SNAKE_CASE(Ex. USER_EMAIL_ADDRESS).

## 3. Formatting and linting expectations
**Frontend:**  
-  Strict mode enabled in TypeScript. Do not use the 'any' type and always declare specific types for variables.
-  Use ESLint and Prettier for formatting.
-  Formatting style: 2-space indentation, single quotes for strings, and semicolons enabled.

**Backend:**  
-  Use Ruff to format Python code.
-  Follow standard Python PEP 8 style rules.
-  Add Python type hints to all function arguments and return types(Ex. def create_alert(rule: AlertRule) -> Alert:).

## 4. Error-Handling Conventions
**Frontend:**  
-  Wrap external API calls in try/catch blocks.
-  Show helpful error popups to users instead of letting the app crash quietly or printing raw errors to the user.

**Backend:**  
-  Throw standard FastAPI HTTPException errors for bad client requests.
-  Never send raw database errors or stack traces back to the client.

## 5. API or service response conventions where applicable
-  All backend endpoints must return consistent JSON data using Pydantic schemas.

## 6. Logging expectations
-  Do not use plain print() statements in production code. Use Python’s built-in logging module.
-  **Log Format:** [TIMESTAMP] [LEVEL] [MODULE]: Message
-  **Log Levels:**
    *  **INFO:** Normal events (Ex. "CSV upload started").
    *  **WARNING:** Non-fatal issues (Ex. "Claude API slow, retrying request").
    *  **ERROR:** Critical failures (Ex. "Database connection failed").
-   **Security Rule:** Never log passwords, Firebase user tokens, or personal customer data.

## 7. Expectations for adding dependencies
**Frontend:**
-  Install packages using npm install <package_name> and consult with the team before adding large component libraries.

  
**Backend:**
-  Keep all dependencies updated in requirements.txt.

  
  **General Rule:**
   -  Do not install a new library if the feature can be built easily with tools already in the project.

## 8. Expectations for testing new or changed behavior
**Backend:**  
-  Write unit tests in pytest for business calculations.
-  Mock external API calls during tests (Ex. mock the Anthropic Claude API so tests do not spend real API credits or depend on an internet connection).

**Frontend:**  
-  Write tests for critical helpers and custom hooks using React Testing Library.

**Pull Request Rule:** Adding a new API route or changing the database must include unit tests or PR will be blocked.# Engineering Coding Standards
