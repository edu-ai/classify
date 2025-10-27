from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import strawberry
from strawberry.fastapi import GraphQLRouter
import sys

app = FastAPI(title="Classify API Gateway", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GraphQL Schema (basic version)
@strawberry.type
class User:
    id: str
    email: str
    name: str

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello from Classify API!"

    @strawberry.field
    def users(self) -> list[User]:
        return [User(id="1", email="test@example.com", name="Test User")]

schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api-gateway"}

@app.get("/")
async def root():
    return {"message": "Classify API Gateway", "graphql_endpoint": "/graphql"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
