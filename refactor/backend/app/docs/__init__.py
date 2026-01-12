"""
API Documentation Module
Serves OpenAPI/Swagger documentation
"""
from flask import Blueprint, send_from_directory, jsonify
import os

docs_bp = Blueprint('docs', __name__, url_prefix='/api/docs')

# Path to the docs directory
DOCS_DIR = os.path.dirname(os.path.abspath(__file__))


@docs_bp.route('/')
def docs_index():
    """Serve Swagger UI HTML"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AlphaGBM API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    <style>
        html { box-sizing: border-box; overflow-y: scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin: 0; background: #fafafa; }
        .topbar { display: none; }
        .swagger-ui .info .title { color: #0D9B97; }
        .swagger-ui .info { margin: 20px 0; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            window.ui = SwaggerUIBundle({
                url: "/api/docs/openapi.yaml",
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                persistAuthorization: true,
                displayRequestDuration: true,
                docExpansion: "list",
                filter: true,
                tagsSorter: "alpha",
                operationsSorter: "alpha"
            });
        };
    </script>
</body>
</html>
'''


@docs_bp.route('/openapi.yaml')
def openapi_spec():
    """Serve the OpenAPI YAML specification"""
    return send_from_directory(DOCS_DIR, 'openapi.yaml', mimetype='text/yaml')


@docs_bp.route('/openapi.json')
def openapi_json():
    """Serve the OpenAPI specification as JSON"""
    import yaml
    yaml_path = os.path.join(DOCS_DIR, 'openapi.yaml')
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        return jsonify(spec)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
