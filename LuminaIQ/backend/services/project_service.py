from db.client import get_supabase_client, async_db
from config.settings import settings
from utils.logger import logger
from typing import List, Dict, Any, Optional
from uuid import uuid4
from collections import Counter

class ProjectService:
    def __init__(self):
        self.client = get_supabase_client()
    
    async def create_project(self, user_id: str, name: str) -> Dict[str, Any]:
        """Create a new project"""
        try:
            response = await async_db(lambda: self.client.table("projects").insert({
                "user_id": user_id,
                "name": name
            }).execute())
            
            if response.data:
                logger.info(f"Created project: {name}")
                return response.data[0]
            else:
                raise Exception("Failed to create project")
                
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            raise

    async def get_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all projects for a user — optimized batch query (no N+1)"""
        try:
            # Single query for all projects
            response = await async_db(
                lambda: self.client.table("projects")
                    .select("*")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .execute()
            )
            
            projects = response.data
            if not projects:
                return []
            
            # Single batch query for ALL document counts (replaces N+1 loop)
            project_ids = [p["id"] for p in projects]
            doc_response = await async_db(
                lambda: self.client.table("documents")
                    .select("project_id")
                    .in_("project_id", project_ids)
                    .execute()
            )
            
            # Build count map in-memory — O(n)
            count_map = Counter(d["project_id"] for d in (doc_response.data or []))
            for p in projects:
                p["docs"] = count_map.get(p["id"], 0)
                
            return projects
        except Exception as e:
            logger.error(f"Error getting projects: {str(e)}")
            return []

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific project"""
        try:
            response = await async_db(
                lambda: self.client.table("projects").select("*").eq("id", project_id).execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting project: {str(e)}")
            return None

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        try:
            await async_db(
                lambda: self.client.table("projects").delete().eq("id", project_id).execute()
            )
            logger.info(f"Deleted project: {project_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting project: {str(e)}")
            return False

project_service = ProjectService()