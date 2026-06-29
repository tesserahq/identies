"""Access rule types constants."""


class AccessRuleTypes:
    """Constants for access rule types/kinds.

    This class holds the valid types of access rules that can be created
    in the system. Each type represents a different way of restricting
    or allowing access based on different criteria.
    """

    # Email-based access rules
    EMAIL = "email"
    """Email-based access rule type. Used for restricting access based on email addresses."""

    # Domain-based access rules
    DOMAIN = "domain"
    """Domain-based access rule type. Used for restricting access based on domain names."""

    _LABELS = {
        EMAIL: "Email",
        DOMAIN: "Domain",
    }

    @classmethod
    def get_all_types(cls) -> list[str]:
        """Get all available access rule types.

        Returns:
            list[str]: A list of all valid access rule types.
        """
        return [cls.EMAIL, cls.DOMAIN]

    @classmethod
    def get_all_options(cls) -> list[dict[str, str]]:
        """Get all access rule types as UI option objects.

        Returns:
            list[dict[str, str]]: Options with ``id`` and ``name`` keys.
        """
        return [{"id": t, "name": cls._LABELS[t]} for t in cls.get_all_types()]

    @classmethod
    def is_valid_type(cls, rule_type: str) -> bool:
        """Check if a given type is valid.

        Args:
            rule_type (str): The access rule type to validate.

        Returns:
            bool: True if the type is valid, False otherwise.
        """
        return rule_type in cls.get_all_types()

    @classmethod
    def get_valid_types_message(cls) -> str:
        """Get a user-friendly message listing all valid types.

        Returns:
            str: A formatted string listing all valid access rule types.
        """
        types = cls.get_all_types()
        return f"Valid access rule types are: {', '.join(types)}"
