from fastapi import APIRouter
from api.v1.endpoints import (
    auth,
    books,
    chat,
    documents,
    mcq,
    evaluation,
    projects,
    notes,
    webhook,
    user_data,
    flashcards,
    mindmaps,
    progress,
    jobs,
    interactive_demo,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(mcq.router, prefix="/mcq", tags=["mcq"])
api_router.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
api_router.include_router(user_data.router, prefix="/user-data", tags=["user-data"])
api_router.include_router(flashcards.router, prefix="/flashcards", tags=["flashcards"])
api_router.include_router(mindmaps.router, prefix="/mindmaps", tags=["mindmaps"])
api_router.include_router(progress.router, prefix="/progress", tags=["progress"])

# Book Store
api_router.include_router(books.router, prefix="/books", tags=["books"])

# Background jobs for heavy AI tasks
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

# Interactive AI-generated HTML demos
api_router.include_router(interactive_demo.router, prefix="/interactive-demo", tags=["interactive-demo"])
