#!/usr/bin/env python3
"""
VSCode AI Statistics Fetcher (Cross-Platform)

Retrieves AI usage statistics from VSCode state databases including:
- Typed characters vs AI-generated characters
- Accepted inline suggestions
- Chat edit counts
- GitHub Copilot account and model information

Works on Windows, macOS, and Linux.
"""

import sqlite3
import json
import sys
import os
from pathlib import Path
from datetime import datetime


def get_vscode_user_dir():
    """
    Get the VSCode User directory based on the operating system.
    
    Returns:
        Path object pointing to VSCode User directory or None if not found
    """
    if sys.platform == "darwin":  # macOS
        path = Path.home() / "Library" / "Application Support" / "Code" / "User"
    elif sys.platform == "win32":  # Windows
        appdata = Path(os.environ.get("APPDATA", ""))
        if not appdata:
            return None
        path = appdata / "Code" / "User"
    else:  # Linux and others
        path = Path.home() / ".config" / "Code" / "User"
    
    return path if path.exists() else None


def extract_ai_stats_from_db(db_path):
    """
    Extract AI statistics from a VSCode state database.
    
    Args:
        db_path: Path to the state.vscdb file
        
    Returns:
        dict with AI stats or None if not found
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get aiStats entry
        cursor.execute("SELECT value FROM ItemTable WHERE key = 'aiStats' LIMIT 1")
        row = cursor.fetchone()
        
        if row:
            stats = json.loads(row[0])
            conn.close()
            return stats
        
        conn.close()
        return None
    except Exception as e:
        return None


def extract_copilot_info_from_db(db_path):
    """
    Extract GitHub Copilot account and configuration from VSCode state database.
    
    Args:
        db_path: Path to the state.vscdb file
        
    Returns:
        dict with Copilot info or None if not found
    """
    info = {}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get Copilot account
        cursor.execute("SELECT value FROM ItemTable WHERE key = 'github.copilot-github' LIMIT 1")
        row = cursor.fetchone()
        if row:
            info["account"] = row[0]
        
        # Get subscription type
        cursor.execute("SELECT value FROM ItemTable WHERE key = 'extensionsAssignmentFilterProvider.copilotSku' LIMIT 1")
        row = cursor.fetchone()
        if row:
            info["subscription"] = row[0]
        
        # Get extension versions
        cursor.execute("SELECT value FROM ItemTable WHERE key = 'extensionsAssignmentFilterProvider.copilotChatExtensionVersion' LIMIT 1")
        row = cursor.fetchone()
        if row:
            info["copilot_chat_version"] = row[0]
        
        cursor.execute("SELECT value FROM ItemTable WHERE key = 'extensionsAssignmentFilterProvider.copilotCompletionsVersion' LIMIT 1")
        row = cursor.fetchone()
        if row:
            info["copilot_completions_version"] = row[0]
        
        # Get active model info from chat session
        cursor.execute("SELECT value FROM ItemTable WHERE key = 'memento/interactive-session-view-copilot' LIMIT 1")
        row = cursor.fetchone()
        if row:
            try:
                session_data = json.loads(row[0])
                if "selectedModel" in session_data:
                    model = session_data["selectedModel"]
                    if "metadata" in model:
                        metadata = model["metadata"]
                        info["active_model"] = {
                            "name": metadata.get("name"),
                            "id": metadata.get("id"),
                            "family": metadata.get("family"),
                            "maxInputTokens": metadata.get("maxInputTokens"),
                            "maxOutputTokens": metadata.get("maxOutputTokens"),
                            "rate": metadata.get("detail")
                        }
            except:
                pass
        
        conn.close()
        return info if info else None
    except Exception as e:
        return None


def fetch_ai_statistics():
    """
    Main function to fetch all AI statistics from VSCode.
    
    Returns:
        dict with complete AI statistics data
    """
    vscode_dir = get_vscode_user_dir()
    
    if not vscode_dir:
        return {
            "error": "VSCode User directory not found",
            "platform": sys.platform
        }
    
    result = {
        "platform": sys.platform,
        "vscode_dir": str(vscode_dir),
        "stats_found": False
    }
    
    # Search for state.vscdb files in workspaceStorage and globalStorage
    db_files = []
    
    # Check global storage first (for account info)
    global_db = vscode_dir / "globalStorage" / "state.vscdb"
    if global_db.exists():
        db_files.append(("global", global_db))
    
    # Check workspace storage (for usage stats)
    workspace_dir = vscode_dir / "workspaceStorage"
    if workspace_dir.exists():
        for workspace_db in workspace_dir.rglob("state.vscdb"):
            db_files.append(("workspace", workspace_db))
    
    # Extract data from databases
    for db_type, db_path in db_files:
        # Get Copilot info (from global or any workspace)
        if "account" not in result:
            copilot_info = extract_copilot_info_from_db(db_path)
            if copilot_info:
                result.update(copilot_info)
        
        # Get AI stats (from workspaces)
        ai_stats = extract_ai_stats_from_db(db_path)
        if ai_stats:
            result["aiStats"] = ai_stats
            result["stats_found"] = True
            result["source_db"] = str(db_path)
            # Found stats, we can stop searching
            break
    
    return result


if __name__ == "__main__":
    stats = fetch_ai_statistics()
    
    # Output as JSON
    print(json.dumps(stats, indent=2))
