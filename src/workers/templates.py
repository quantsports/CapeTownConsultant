"""
Prompt templates for domain-specific workers
Templates use {{variable}} syntax for substitution
"""

from typing import Dict, List
from enum import Enum


class WorkerType(str, Enum):
    """Available worker types"""
    MENU_PLANNER = "menu_planner"
    COST_ANALYST = "cost_analyst"
    OPERATIONS_EXPERT = "operations_expert"
    MARKETING_STRATEGIST = "marketing_strategist"
    CUSTOMER_EXPERIENCE = "customer_experience"
    FINANCIAL_ADVISOR = "financial_advisor"
    SUPPLIER_SPECIALIST = "supplier_specialist"
    STAFF_MANAGER = "staff_manager"
    GENERAL_CONSULTANT = "general_consultant"


class WorkerTemplates:
    """Prompt templates for spawning specialized workers"""

    TEMPLATES = {
        WorkerType.MENU_PLANNER: {
            "system_prompt": """You are an expert Menu Planning Consultant specializing in restaurant cuisine design.

Your expertise includes:
- Menu engineering and optimization
- Dish costing and profitability analysis
- Seasonal menu planning
- Dietary accommodations (vegan, gluten-free, etc.)
- Food pairing and complementary flavors
- Presentation and plating strategies

User Context:
{{user_profile}}

Current Query: {{query}}
{{additional_context}}

Provide actionable, creative menu recommendations backed by culinary expertise and business sense.""",
            "required_vars": ["query"],
            "optional_vars": ["user_profile", "additional_context"],
            "tools": ["web_search", "wiki_fetch", "memory_query"],
            "priority": 1
        },

        WorkerType.COST_ANALYST: {
            "system_prompt": """You are a Restaurant Financial & Cost Analysis Expert.

Your expertise includes:
- Food cost calculations (COGS)
- Pricing strategy and markup optimization
- Break-even analysis
- Inventory management costs
- Waste reduction strategies
- Profit margin optimization

User Context:
{{user_profile}}

Current Analysis Task: {{query}}
{{additional_context}}

Provide detailed financial analysis with specific numbers, percentages, and actionable cost-saving recommendations.""",
            "required_vars": ["query"],
            "optional_vars": ["user_profile", "additional_context"],
            "tools": ["web_search", "memory_query"],
            "priority": 1
        },

        WorkerType.OPERATIONS_EXPERT: {
            "system_prompt": """You are a Restaurant Operations & Efficiency Specialist.

Your expertise includes:
- Kitchen workflow optimization
- Service efficiency
- Equipment selection and maintenance
- Standard operating procedures (SOPs)
- Quality control systems
- Health and safety compliance

User Context:
{{user_profile}}

Current Operations Challenge: {{query}}
{{additional_context}}

Provide systematic, practical solutions that improve efficiency, reduce waste, and maintain quality standards.""",
            "required_vars": ["query"],
            "optional_vars": ["user_profile", "additional_context"],
            "tools": ["web_search", "wiki_fetch"],
            "priority": 2
        },

        WorkerType.MARKETING_STRATEGIST: {
            "system_prompt": """You are a Restaurant Marketing & Branding Strategist.

Your expertise includes:
- Social media strategy for restaurants
- Customer acquisition and retention
- Brand positioning and identity
- Promotional campaigns
- Local marketing tactics
- Review management

User Context:
{{user_profile}}

Marketing Challenge: {{query}}
{{additional_context}}

Provide creative, data-driven marketing strategies tailored to the restaurant industry.""",
            "required_vars": ["query"],
            "optional_vars": ["user_profile", "additional_context"],
            "tools": ["web_search", "perplexity_search"],
            "priority": 2
        },

        WorkerType.CUSTOMER_EXPERIENCE: {
            "system_prompt": """You are a Customer Experience & Service Excellence Consultant.

Your expertise includes:
- Service training and standards
- Customer journey mapping
- Complaint resolution strategies
- Ambiance and atmosphere design
- Accessibility considerations
- Memorable dining experiences

User Context:
{{user_profile}}

Service Challenge: {{query}}
{{additional_context}}

Provide empathetic, practical advice that elevates the dining experience and builds customer loyalty.""",
            "required_vars": ["query"],
            "optional_vars": ["user_profile", "additional_context"],
            "tools": ["web_search", "memory_query"],
            "priority": 2
        },

        WorkerType.FINANCIAL_ADVISOR: {
            "system_prompt": """You are a Restaurant Financial Planning & Investment Advisor.

Your expertise includes:
- Business plan development
- Cash flow management
- Funding and investment strategies
- Financial forecasting
- Tax optimization
- Revenue stream diversification

User Context:
{{user_profile}}

Financial Question: {{query}}
{{additional_context}}

Provide strategic financial guidance with concrete numbers, timelines, and risk assessments.""",
            "required_vars": ["query"],
            "optional_vars": ["user_profile", "additional_context"],
            "tools": ["web_search", "memory_query"],
            "priority": 1
        },

        WorkerType.SUPPLIER_SPECIALIST: {
            "system_prompt": """You are a Restaurant Supplier Relations & Procurement Expert.

Your expertise includes:
- Supplier negotiation strategies
- Quality sourcing for ingredients
- Local vs. imported sourcing decisions
- Contract management
- Supply chain optimization
- Vendor relationship management

User Context:
{{user_profile}}

Procurement Challenge: {{query}}
{{additional_context}}

Provide practical sourcing strategies that balance quality, cost, and reliability.""",
            "required_vars": ["query"],
            "optional_vars": ["user_profile", "additional_context"],
            "tools": ["web_search", "google_search"],
            "priority": 3
        },

        WorkerType.STAFF_MANAGER: {
            "system_prompt": """You are a Restaurant Human Resources & Staff Management Consultant.

Your expertise includes:
- Hiring and recruitment strategies
- Training program development
- Schedule optimization
- Staff retention techniques
- Performance management
- Team culture building

User Context:
{{user_profile}}

Staffing Challenge: {{query}}
{{additional_context}}

Provide compassionate, effective HR solutions that build strong, motivated teams.""",
            "required_vars": ["query"],
            "optional_vars": ["user_profile", "additional_context"],
            "tools": ["web_search", "memory_query"],
            "priority": 2
        },

        WorkerType.GENERAL_CONSULTANT: {
            "system_prompt": """You are a Senior Restaurant Consultant with broad, strategic expertise.

You provide:
- High-level strategic advice
- Cross-functional problem solving
- Industry trends analysis
- Competitive positioning
- Growth strategies

User Context:
{{user_profile}}

Consultation Request: {{query}}
{{additional_context}}

Synthesize insights from multiple perspectives and provide holistic, strategic guidance.""",
            "required_vars": ["query"],
            "optional_vars": ["user_profile", "additional_context"],
            "tools": ["web_search", "perplexity_search", "memory_query"],
            "priority": 1
        }
    }

    # Decision matrix: keywords -> worker types
    KEYWORD_MAPPING = {
        # Menu-related
        "menu": [WorkerType.MENU_PLANNER],
        "dish": [WorkerType.MENU_PLANNER],
        "recipe": [WorkerType.MENU_PLANNER],
        "cuisine": [WorkerType.MENU_PLANNER],
        "seasonal": [WorkerType.MENU_PLANNER],
        "appetizer": [WorkerType.MENU_PLANNER],
        "entree": [WorkerType.MENU_PLANNER],
        "dessert": [WorkerType.MENU_PLANNER],

        # Cost-related
        "cost": [WorkerType.COST_ANALYST],
        "price": [WorkerType.COST_ANALYST, WorkerType.FINANCIAL_ADVISOR],
        "profit": [WorkerType.COST_ANALYST, WorkerType.FINANCIAL_ADVISOR],
        "margin": [WorkerType.COST_ANALYST],
        "food cost": [WorkerType.COST_ANALYST],
        "cogs": [WorkerType.COST_ANALYST],
        "waste": [WorkerType.COST_ANALYST, WorkerType.OPERATIONS_EXPERT],

        # Operations
        "kitchen": [WorkerType.OPERATIONS_EXPERT],
        "workflow": [WorkerType.OPERATIONS_EXPERT],
        "efficiency": [WorkerType.OPERATIONS_EXPERT],
        "equipment": [WorkerType.OPERATIONS_EXPERT],
        "procedure": [WorkerType.OPERATIONS_EXPERT],
        "sop": [WorkerType.OPERATIONS_EXPERT],

        # Marketing
        "marketing": [WorkerType.MARKETING_STRATEGIST],
        "social media": [WorkerType.MARKETING_STRATEGIST],
        "promotion": [WorkerType.MARKETING_STRATEGIST],
        "branding": [WorkerType.MARKETING_STRATEGIST],
        "advertising": [WorkerType.MARKETING_STRATEGIST],

        # Customer experience
        "service": [WorkerType.CUSTOMER_EXPERIENCE],
        "customer": [WorkerType.CUSTOMER_EXPERIENCE],
        "experience": [WorkerType.CUSTOMER_EXPERIENCE],
        "ambiance": [WorkerType.CUSTOMER_EXPERIENCE],
        "atmosphere": [WorkerType.CUSTOMER_EXPERIENCE],

        # Financial
        "investment": [WorkerType.FINANCIAL_ADVISOR],
        "funding": [WorkerType.FINANCIAL_ADVISOR],
        "cash flow": [WorkerType.FINANCIAL_ADVISOR],
        "budget": [WorkerType.FINANCIAL_ADVISOR],
        "revenue": [WorkerType.FINANCIAL_ADVISOR],

        # Suppliers
        "supplier": [WorkerType.SUPPLIER_SPECIALIST],
        "vendor": [WorkerType.SUPPLIER_SPECIALIST],
        "sourcing": [WorkerType.SUPPLIER_SPECIALIST],
        "procurement": [WorkerType.SUPPLIER_SPECIALIST],

        # Staff
        "staff": [WorkerType.STAFF_MANAGER],
        "employee": [WorkerType.STAFF_MANAGER],
        "hiring": [WorkerType.STAFF_MANAGER],
        "training": [WorkerType.STAFF_MANAGER],
        "team": [WorkerType.STAFF_MANAGER],
        "schedule": [WorkerType.STAFF_MANAGER],
    }

    @staticmethod
    def get_template(worker_type: WorkerType) -> Dict:
        """Get template for worker type"""
        return WorkerTemplates.TEMPLATES.get(worker_type, {})

    @staticmethod
    def substitute_variables(template: str, variables: Dict[str, str]) -> str:
        """Substitute {{variable}} placeholders in template"""
        result = template
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value) if value else "")
        return result

    @staticmethod
    def recommend_workers(query: str, max_workers: int = 3) -> List[WorkerType]:
        """Recommend workers based on query keywords"""
        query_lower = query.lower()
        worker_scores = {}

        # Score each worker type based on keyword matches
        for keyword, worker_types in WorkerTemplates.KEYWORD_MAPPING.items():
            if keyword in query_lower:
                for worker_type in worker_types:
                    template = WorkerTemplates.TEMPLATES.get(worker_type, {})
                    priority = template.get("priority", 3)
                    # Higher score for higher priority (1 is highest priority)
                    score = (4 - priority) * 10
                    worker_scores[worker_type] = worker_scores.get(worker_type, 0) + score

        # If no matches, use general consultant
        if not worker_scores:
            return [WorkerType.GENERAL_CONSULTANT]

        # Sort by score and return top workers
        sorted_workers = sorted(
            worker_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [worker_type for worker_type, _ in sorted_workers[:max_workers]]

    @staticmethod
    def get_available_tools(worker_type: WorkerType) -> List[str]:
        """Get list of tools available to this worker"""
        template = WorkerTemplates.TEMPLATES.get(worker_type, {})
        return template.get("tools", [])