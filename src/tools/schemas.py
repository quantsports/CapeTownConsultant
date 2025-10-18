"""
Tool schemas and validation
JSON schemas for function calling
"""

from typing import Dict, Any, List


class ToolSchemas:
    """Tool schema definitions and validators"""

    # Validation schemas for each tool
    SCHEMAS = {
        "web_search": {
            "required": ["query"],
            "optional": {"num": int}
        },
        "google_search": {
            "required": ["query"],
            "optional": {"num": int}
        },
        "perplexity_search": {
            "required": ["query"],
            "optional": {}
        },
        "kagi_search": {
            "required": ["query"],
            "optional": {"allow_cache": bool}
        },
        "wiki_fetch": {
            "required": ["query"],
            "optional": {"limit": int}
        },
        "memory_query": {
            "required": ["text"],
            "optional": {"top_k": int, "filter": dict}
        },
        "memory_upsert": {
            "required": ["items"],
            "optional": {}
        },
        "profile_read": {
            "required": [],  # ✅ FIXED: Made keys optional to allow reading full profile
            "optional": {"keys": list}
        },
        "profile_write": {
            "required": ["data"],
            "optional": {}
        },
        "list_memories": {
            "required": [],
            "optional": {
                "limit": int,
                "offset": int,
                "sort_by": str
            }
        },
        "search_memories": {
            "required": ["query"],
            "optional": {
                "top_k": int,
                "min_score": float
            }
        },
        "get_memory_stats": {
            "required": [],
            "optional": {}
        },
        "delete_memory": {
            "required": ["memory_id"],
            "optional": {}
        },
        "export_memories": {
            "required": [],
            "optional": {
                "format": str,
                "include_profile": bool
            }
        }
    }

    @staticmethod
    def get_function_definitions() -> List[Dict[str, Any]]:
        """Get OpenAI function definitions"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": """Search web using SerpAPI. COST: Low ($0.002). USE FOR: Current events, news, simple facts. TIP: Default choice for most queries.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "num": {
                                "type": "integer",
                                "description": "Results (default 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "google_search",
                    "description": """Google Custom Search. COST: Medium ($0.005). USE: Fallback when SerpAPI unavailable.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "num": {"type": "integer", "default": 5}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "perplexity_search",
                    "description": """Perplexity AI. COST: High. USE ONLY FOR: Complex analysis, synthesis, multi-source integration.""",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "kagi_search",
                    "description": """Kagi FastGPT. COST: Medium ($0.015/query, 1.5¢). USE FOR: AI-synthesized answers with live web search backing. Complex questions requiring synthesis, current events, technical deep-dives. Cached responses are FREE.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query or question to answer"
                            },
                            "allow_cache": {
                                "type": "boolean",
                                "description": "Allow cached responses (default: true, free if cached)",
                                "default": True
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "wiki_fetch",
                    "description": """Wikipedia. COST: Free. USE FIRST for: Encyclopedic knowledge, definitions, facts.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Wikipedia search query"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max results (default 3)",
                                "default": 3
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_query",
                    "description": """Query vector memory for relevant past conversations and context.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Query text to search memory"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results (default 5)",
                                "default": 5
                            },
                            "filter": {
                                "type": "object",
                                "description": "Optional metadata filter"
                            }
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_upsert",
                    "description": """Store information in vector memory for future recall. System auto-generates IDs.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "description": "List of items to store. Each needs 'text' field, optional 'meta' for metadata.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {
                                            "type": "string",
                                            "description": "The content to store"
                                        },
                                        "meta": {
                                            "type": "object",
                                            "description": "Optional metadata (e.g., category, importance)"
                                        }
                                    },
                                    "required": ["text"]  # ✅ FIXED: Only text is required, ID auto-generated
                                }
                            }
                        },
                        "required": ["items"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "profile_read",
                    "description": """Read user profile data. Omit 'keys' parameter to get full profile.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keys": {
                                "type": "array",
                                "description": "Optional: Specific keys to read. If omitted, returns entire profile.",
                                "items": {"type": "string"}
                            }
                        },
                        "required": []  # ✅ FIXED: No required params - can read full profile
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "profile_write",
                    "description": """Write/update user profile data (preferences, history, settings).""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "object",
                                "description": "Profile data to write (key-value pairs)"
                            }
                        },
                        "required": ["data"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_memories",
                    "description": """List stored memories with filtering and pagination. View what has been stored in memory.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of memories to return (default 50)",
                                "default": 50
                            },
                            "offset": {
                                "type": "integer",
                                "description": "Number of memories to skip for pagination (default 0)",
                                "default": 0
                            },
                            "sort_by": {
                                "type": "string",
                                "description": "Sort order: 'newest', 'oldest', 'score_desc', 'score_asc' (default 'newest')",
                                "enum": ["newest", "oldest", "score_desc", "score_asc"],
                                "default": "newest"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_memories",
                    "description": """Search stored memories semantically. Find relevant memories using natural language queries.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query to find relevant memories"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return (default 20)",
                                "default": 20
                            },
                            "min_score": {
                                "type": "number",
                                "description": "Minimum similarity score threshold 0.0-1.0 (default 0.7)",
                                "default": 0.7
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_memory_stats",
                    "description": """Get statistics about stored memories including count, date ranges, and profile info.""",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_memory",
                    "description": """Delete a specific memory by ID. Use with caution.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "memory_id": {
                                "type": "string",
                                "description": "ID of the memory to delete"
                            }
                        },
                        "required": ["memory_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "export_memories",
                    "description": """Export all memories for the user in JSON or CSV format.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "format": {
                                "type": "string",
                                "description": "Export format: 'json' or 'csv' (default 'json')",
                                "enum": ["json", "csv"],
                                "default": "json"
                            },
                            "include_profile": {
                                "type": "boolean",
                                "description": "Include profile data in export (default true)",
                                "default": True
                            }
                        },
                        "required": []
                    }
                }
            }
        ]

    @staticmethod
    def validate_args(tool_name: str, args: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate tool arguments against schema

        Args:
            tool_name: Name of the tool
            args: Arguments to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if tool_name not in ToolSchemas.SCHEMAS:
            return False, f"Unknown tool: {tool_name}"

        schema = ToolSchemas.SCHEMAS[tool_name]

        # Check required parameters
        for param in schema["required"]:
            if param not in args:
                return False, f"Missing required parameter: {param}"

        # Validate optional parameter types
        for param, param_type in schema["optional"].items():
            if param in args and not isinstance(args[param], param_type):
                return False, f"Invalid type for {param}: expected {param_type.__name__}"

        return True, ""

    @staticmethod
    def get_tool_names() -> List[str]:
        """Get list of all available tool names"""
        return list(ToolSchemas.SCHEMAS.keys())