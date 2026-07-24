# Sahaayak AI — Frontend

The user-facing React application for Sahaayak AI. It provides a responsive, bilingual (Hindi/English) interface for patients to report symptoms naturally and receive AI-driven triage guidance.

## Features

- **Bilingual Interface**: Full toggle between English and हिन्दी (Hindi) using custom `i18n` translations.
- **Natural Chat UI**: Conversational interface connected to the Groq + OpenSearch backend.
- **Triage Reports**: View past consultations and download reports securely using `jsPDF`.
- **JWT Authentication**: Secure login, registration, and user session management via `AuthContext`.
- **Responsive Design**: Built to work seamlessly across mobile, tablet, and desktop devices.
- **Hospital Finder**: Integrated OpenStreetMap UI to locate nearby healthcare facilities.

## Prerequisites

- Node.js 18+
- The Sahaayak FastAPI backend must be running locally (default: `http://localhost:8000`) for the API calls to succeed.

## Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Run the Application
```bash
npm start
```
Runs the app in development mode. Open [http://localhost:3000](http://localhost:3000) to view it in your browser. The page will reload when you make changes.

### 3. Build for Production
```bash
npm run build
```
Builds the app for production to the `build` folder. It correctly bundles React in production mode and optimizes the build for the best performance.

## Project Structure

```text
src/
├── components/       # Reusable UI elements (Sidebar, VitalsIntake, TriageDemoPanel)
├── context/          # Global state management (AuthContext, LanguageContext)
├── i18n/             # Translation dictionaries for English and Hindi
└── pages/            # Main application views (Dashboard, Consultation, Reports, Login)
```