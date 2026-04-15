from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.routes.categorias_routes import router as categorias_router
from app.routes.clientes_routes import router as clientes_router
from app.routes.facturas_routes import router as facturas_router
from app.routes.movimientos_routes import router as movimientos_router
from app.routes.producto_routes import router as productos_router
from app.routes.reportes_routes import router as reportes_router

app = FastAPI(
    title="INV-BILL-CORE",
    description="Backend API for point of sale, inventory control and operational reporting",
    version="1.0.0",
)

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path("image")
if static_dir.exists() and static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def index():
    return {"message": "INV-BILL-CORE operativo"}


app.include_router(categorias_router)
app.include_router(productos_router)
app.include_router(clientes_router)
app.include_router(movimientos_router)
app.include_router(facturas_router)
app.include_router(reportes_router)
