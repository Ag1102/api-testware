from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, validator
import httpx
import os
import base64
import typing as t
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Crear instancia de FastAPI
app = FastAPI(
    title="Azure DevOps Proxy API",
    description="Expose endpoints to list projects and create Bugs in Azure DevOps",
    version="1.0.0",
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Funciones de configuración
def get_azure_config() -> t.Tuple[str, str]:
    org = os.getenv("AZURE_DEVOPS_ORG")
    pat = os.getenv("AZURE_DEVOPS_PAT")
    if not org or not pat:
        raise RuntimeError(
            "Error: El servidor no tiene la configuración necesaria (AZURE_DEVOPS_ORG, AZURE_DEVOPS_PAT)."
        )
    return org, pat


def build_auth_header(pat: str) -> str:
    token = f":{pat}".encode("utf-8")
    b64 = base64.b64encode(token).decode("utf-8")
    return f"Basic {b64}"


# Modelo de entrada para crear Bugs
class BugCreateRequest(BaseModel):
    project: str
    userStoryId: int
    title: str
    assignedTo: EmailStr
    reproSteps: str
    effort: float
    cliente: str
    priority: int = Field(..., ge=1, le=4)
    severity: str
    activity: str
    tipoDeError: str
    fechaInicioPlaneada: str
    responsableBug: EmailStr
    aplicacion: str
    tareaAsociada: int
    versionAplicacion: str
    funcionalidad: str

    @validator("fechaInicioPlaneada")
    def validate_fecha(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("fechaInicioPlaneada debe tener el formato YYYY-MM-DD")
        return v


# Manejo de errores
@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )


@app.exception_handler(httpx.HTTPError)
async def httpx_error_handler(request: Request, exc: httpx.HTTPError):
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": f"Error en la comunicación con Azure DevOps: {str(exc)}"},
    )


# Endpoint: listar proyectos
@app.get("/projects")
async def list_projects():
    org, pat = get_azure_config()

    url = f"https://dev.azure.com/{org}/_apis/projects?api-version=7.1-preview"
    headers = {
        "Authorization": build_auth_header(pat),
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code >= 400:
        try:
            content = resp.json()
        except Exception:
            content = {"raw_text": resp.text}
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Azure DevOps API error fetching projects",
                "azure_status": resp.status_code,
                "azure_response": content,
            },
        )

    return resp.json()


# Función auxiliar: buscar usuario en Azure DevOps
async def find_user_principal_name(
    org: str, pat: str, display_name: str
) -> t.Optional[str]:
    url = (
        f"https://vsaex.dev.azure.com/{org}/_apis/userentitlements"
        f"?api-version=6.0-preview.3&$filter=name eq '{display_name}'"
    )
    headers = {
        "Authorization": build_auth_header(pat),
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code >= 400:
        return None

    data = resp.json()
    users = data.get("members") or data.get("value") or []

    for user in users:
        name = user.get("user", {}).get("displayName") or user.get("name", "")
        if name.strip().lower() == display_name.strip().lower():
            principal = user.get("user", {}).get("principalName")
            if principal:
                return principal
            mail = user.get("user", {}).get("mailAddress")
            if mail:
                return mail

    return None


# Endpoint: crear bug
@app.post("/bugs", status_code=status.HTTP_201_CREATED)
async def create_bug(request_body: BugCreateRequest):
    org, pat = get_azure_config()

    fecha_con_hora = f"{request_body.fechaInicioPlaneada}T00:00:00-05:00"
    TESTER_NAME = "Antony Daniel Gutierrez Salgado"
    tester_principal = await find_user_principal_name(org, pat, TESTER_NAME)

    if not tester_principal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se pudo encontrar el usuario Tester '{TESTER_NAME}' en la organización de Azure DevOps.",
        )

    project = request_body.project
    url = f"https://dev.azure.com/{org}/{project}/_apis/wit/workitems/$Bug?api-version=7.1-preview"

    headers = {
        "Authorization": build_auth_header(pat),
        "Content-Type": "application/json-patch+json",
        "Accept": "application/json",
    }

    patch_ops = [
        {"op": "add", "path": "/fields/System.Title", "value": request_body.title},
        {
            "op": "add",
            "path": "/fields/System.AssignedTo",
            "value": request_body.assignedTo,
        },
        {
            "op": "add",
            "path": "/fields/Microsoft.VSTS.TCM.ReproSteps",
            "value": request_body.reproSteps,
        },
        {
            "op": "add",
            "path": "/fields/Microsoft.VSTS.Scheduling.Effort",
            "value": request_body.effort,
        },
        {
            "op": "add",
            "path": "/fields/Microsoft.VSTS.Common.Priority",
            "value": request_body.priority,
        },
        {
            "op": "add",
            "path": "/fields/Microsoft.VSTS.Common.Severity",
            "value": request_body.severity,
        },
        {
            "op": "add",
            "path": "/fields/Microsoft.VSTS.Common.Activity",
            "value": request_body.activity,
        },
        {
            "op": "add",
            "path": "/fields/Microsoft.VSTS.Common.ValueArea",
            "value": "Business",
        },
        {"op": "add", "path": "/fields/Custom.Tester", "value": tester_principal},
        {"op": "add", "path": "/fields/Custom.Cliente", "value": request_body.cliente},
        {
            "op": "add",
            "path": "/fields/Custom.Tipodeerror",
            "value": request_body.tipoDeError,
        },
        {
            "op": "add",
            "path": "/fields/Custom.FechaInicioPlaneada",
            "value": fecha_con_hora,
        },
        {
            "op": "add",
            "path": "/fields/Custom.ResponsableBug",
            "value": request_body.responsableBug,
        },
        {
            "op": "add",
            "path": "/fields/Custom.33ece249-f3ca-4b23-a86a-0c605534caa3",
            "value": request_body.aplicacion,
        },
        {
            "op": "add",
            "path": "/fields/Custom.Tareaasociada",
            "value": str(request_body.tareaAsociada),
        },
        {
            "op": "add",
            "path": "/fields/Custom.f82dc49a-eb67-44c3-ac65-de18fee91f0b",
            "value": request_body.versionAplicacion,
        },
        {
            "op": "add",
            "path": "/fields/Custom.Funcionalidadquepresentaelerror",
            "value": request_body.funcionalidad,
        },
        {
            "op": "add",
            "path": "/relations/-",
            "value": {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"https://dev.azure.com/{org}/{project}/_apis/wit/workItems/{request_body.userStoryId}",
                "attributes": {"comment": "Parent User Story"},
            },
        },
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, json=patch_ops)

    if resp.status_code >= 400:
        try:
            azure_body = resp.json()
        except Exception:
            azure_body = {"raw_text": resp.text}
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Azure DevOps API error creating bug",
                "azure_status": resp.status_code,
                "azure_response": azure_body,
            },
        )

    try:
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=resp.json())
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED, content={"raw_text": resp.text}
        )


# Solo para desarrollo local
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
