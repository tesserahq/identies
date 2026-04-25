class AccessRuleError(Exception):
    pass


class AccessRuleAlreadyExistsError(AccessRuleError):
    pass
