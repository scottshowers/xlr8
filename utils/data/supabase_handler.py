"""
Supabase Database Handler
Functions for saving, loading, and deleting projects from Supabase
"""

from config import AppConfig


def get_supabase_client():
    """Get Supabase client instance"""
    try:
        from supabase import create_client
        client = create_client(AppConfig.SUPABASE_URL, AppConfig.SUPABASE_KEY)
        return client
    except Exception as e:
        print(f"Error creating Supabase client: {e}")
        return None


def save_project(project_data):
    """
    Save a project to Supabase
    
    Args:
        project_data: Dictionary with project info
    
    Returns:
        Boolean indicating success
    """
    try:
        client = get_supabase_client()
        if not client:
            return False
        
        # Upsert (insert or update) the project
        response = client.table('projects').upsert(project_data).execute()
        
        print(f"✅ Saved project to Supabase: {project_data.get('name')}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving project to Supabase: {e}")
        return False


def get_all_projects():
    """
    Get all projects from Supabase
    
    Returns:
        List of project dictionaries
    """
    try:
        client = get_supabase_client()
        if not client:
            return []
        
        response = client.table('projects').select('*').execute()
        
        projects = response.data if response.data else []
        print(f"✅ Loaded {len(projects)} projects from Supabase")
        return projects
        
    except Exception as e:
        print(f"❌ Error fetching projects from Supabase: {e}")
        return []


def get_project(project_name):
    """
    Get a specific project from Supabase
    
    Args:
        project_name: Name of the project to retrieve
    
    Returns:
        Project dictionary or None
    """
    try:
        client = get_supabase_client()
        if not client:
            return None
        
        response = client.table('projects').select('*').eq('name', project_name).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
        
    except Exception as e:
        print(f"❌ Error fetching project from Supabase: {e}")
        return None


def delete_project(project_name):
    """
    Delete a project from Supabase
    
    Args:
        project_name: Name of the project to delete
    
    Returns:
        Boolean indicating success
    """
    try:
        client = get_supabase_client()
        if not client:
            return False
        
        response = client.table('projects').delete().eq('name', project_name).execute()
        
        print(f"✅ Deleted project from Supabase: {project_name}")
        return True
        
    except Exception as e:
        print(f"❌ Error deleting project from Supabase: {e}")
        return False


def update_project(project_name, updates):
    """
    Update specific fields of a project
    
    Args:
        project_name: Name of the project to update
        updates: Dictionary of fields to update
    
    Returns:
        Boolean indicating success
    """
    try:
        client = get_supabase_client()
        if not client:
            return False
        
        response = client.table('projects').update(updates).eq('name', project_name).execute()
        
        print(f"✅ Updated project in Supabase: {project_name}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating project in Supabase: {e}")
        return False
