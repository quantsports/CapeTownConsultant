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
            "required": ["keys"],
            "optional": {}
        },
        "profile_write": {
            "required": ["data"],
            "optional": {}
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
                    "description": """Store information in vector memory for future recall.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "description": "List of items to store",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "text": {"type": "string"},
                                        "metadata": {"type": "object"}
                                    },
                                    "required": ["id", "text"]
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
                    "description": """Read user profile data (preferences, history, settings).""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keys": {
                                "type": "array",
                                "description": "List of profile keys to read",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["keys"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "profile_write",
                    "description": """Write user profile data (preferences, history, settings).""",
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