from agents.workflow_graph import create_ticket_workflow


def generate_workflow_diagram():
    """Generate PNG diagram of LangGraph workflow"""

    # Create workflow
    workflow = create_ticket_workflow()

    # Generate diagram
    graph = workflow.get_graph()
    png_data = graph.draw_mermaid_png()

    with open("workflow_diagram.png", "wb") as f:
        f.write(png_data)

    print("✅ Workflow diagram saved to workflow_diagram.png")

# TODO:
# def generate_mermaid_text():
#     """Generate Mermaid diagram code"""

#     workflow = create_ticket_workflow()
#     graph = workflow.get_graph()
#     mermaid_code = graph.draw_mermaid()

#     with open("workflow_diagram.md", "w") as f:
#         f.write(f"```mermaid\n{mermaid_code}\n```")
    


if __name__ == "__main__":
    generate_workflow_diagram()
    # generate_mermaid_text()
