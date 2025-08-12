# FastAPI Azure DevOps Proxy API

This project is a FastAPI application that serves as a proxy for interacting with the Azure DevOps API. It provides endpoints to list projects and create bugs in Azure DevOps.

## Project Structure

```
fastapi-vercel-app
├── api
│   └── index.py          # Contains the FastAPI application and API endpoints
├── requirements.txt       # Lists the dependencies required for the project
├── vercel.json            # Configuration for deploying the FastAPI application on Vercel
└── README.md              # Documentation for the project
```

## Requirements

To run this project, you need to have the following dependencies installed:

- FastAPI
- httpx
- mangum
- python-dotenv

You can install the required dependencies using the following command:

```
pip install -r requirements.txt
```

## Environment Variables

Before running the application, make sure to set the following environment variables in a `.env` file or in your environment:

- `AZURE_DEVOPS_ORG`: Your Azure DevOps organization name.
- `AZURE_DEVOPS_PAT`: Your Azure DevOps Personal Access Token.

## Running the Application

To run the FastAPI application locally, use the following command:

```
uvicorn api.index:app --reload
```

This will start the server at `http://127.0.0.1:8000`.

## Deploying on Vercel

To deploy the application on Vercel, follow these steps:

1. Create a Vercel account if you don't have one.
2. Install the Vercel CLI globally:

   ```
   npm install -g vercel
   ```

3. Run the following command in the project directory to deploy:

   ```
   vercel
   ```

4. Follow the prompts to complete the deployment process.

## API Endpoints

### List Projects

- **Endpoint:** `GET /projects`
- **Description:** Fetches a list of projects from Azure DevOps.

### Create Bug

- **Endpoint:** `POST /bugs`
- **Description:** Creates a new bug in Azure DevOps. Requires a JSON body with the bug details.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.