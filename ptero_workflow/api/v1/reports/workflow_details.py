from flask import g


def report(workflow_id):
    return g.backend.get_workflow_details(workflow_id)
