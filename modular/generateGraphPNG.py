from langchain_core.runnables.graph import MermaidDrawMethod



def generate_graph_png(app,filename):

    # Generate the PNG using MermaidDrawMethod.API
    png_data = app.get_graph().draw_mermaid_png(
        draw_method=MermaidDrawMethod.API,
    )

    # Save the PNG data to a file
    output_file = filename
    with open(output_file, "wb") as file:
        file.write(png_data)

    print(f"PNG graph has been saved to {output_file}")
    
