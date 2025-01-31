#!/usr/bin/env python3

import ast
import getpass
import json
import logging
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional
import shutil

import requests
import tomli
import tomli_w
import typer
import urllib3
from requests.models import Response
from typing_extensions import Annotated
from urllib3.exceptions import InsecureRequestWarning

__version__ = "0.6.1"

log = logging.getLogger(__name__)

cli = typer.Typer()


class MethodVisitor(ast.NodeVisitor):
    """AST visitor that finds methods decorated with 'expose.tool'"""

    def __init__(self):
        self.exposed_methods: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition and check its methods"""
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                # Check if the method has any decorators
                for decorator in item.decorator_list:
                    # Check if decorator is 'truffle.tool'
                    if isinstance(decorator, ast.Attribute):
                        if (
                            isinstance(decorator.value, ast.Name)
                            and decorator.value.id == "truffle"
                            and decorator.attr == "tool"
                        ):
                            self.exposed_methods.append(item.name)
                    elif (
                        isinstance(decorator, ast.Name)
                        and decorator.id == "expose_tool"
                    ):
                        self.exposed_methods.append(item.name)


def _validate_main_py(main_py_file: Path) -> bool:
    """
    A valid Truffle app must create a valid TruffleApp instance and call launch!
    """
    main_py_text: str = main_py_file.read_text()
    if "import truffle" not in main_py_text:
        log.error("The main.py script doesn't import truffle!")
        return False
    if ".launch()" not in main_py_text:
        log.error(".launch() call not detected in your TruffleApp!")
        return False
    return True


def _validate_truffle_json(truffle_manifest_path: Path) -> bool:
    """
    A valid Truffle app must have a manifest.json file to be indexed by the agent.
    """
    manifest: dict[str, Any] = json.loads(truffle_manifest_path.read_text())
    for required_key in {"name", "example_prompts", "description"}:
        if required_key not in manifest.keys():
            log.error(f"manifest.json is missing key {required_key}")
            return False
    # TODO: improve validation here
    return True


def _validate_requirements_txt(requirements_file: Path) -> bool:
    """
    Check if the requirements.txt file contains a "truffle" package with version constraints.

    Args:
        requirements_path (Path): Path to the requirements.txt file

    Returns:
        bool: True if "truffle" package is found with version constraints, False otherwise
    """
    try:
        content = requirements_file.read_text()

        # Split content into lines and strip whitespace
        lines = [line.strip() for line in content.splitlines()]

        # Filter out comments and empty lines
        package_lines = [line for line in lines if line and not line.startswith("#")]

        # remove truffle from deps
        truffle_free_lines = [
            line for line in package_lines if not line.startswith("truffle")
        ]

        os.remove(requirements_file)
        requirements_file.write_text("\n".join(truffle_free_lines))
        return True

    except (FileNotFoundError, PermissionError):
        log.error("requirements.txt encountered an error", exc_info=True)
        return False


def _assemble_zip(dir_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Create a zip file from a directory and all its contents, ensuring the directory
    itself is the top-level folder in the zip.

    Args:
        dir_path (Path): Path to the directory to zip
        output_path (Optional[Path]): Path where the zip file should be created.
            If not provided, creates the zip file in the parent directory
            with the same name as the input directory.

    Returns:
        Path: Path to the created zip file

    Raises:
        NotADirectoryError: If dir_path is not a directory
        FileExistsError: If output_path already exists
    """
    if not dir_path.is_dir():
        raise NotADirectoryError(f"{dir_path} is not a directory")

    # If no output path specified, create zip in parent dir with same name
    if output_path is None:
        output_path = dir_path.parent / f"{dir_path.name}.truffle"

    # Ensure we don't overwrite existing files
    if output_path.exists():
        raise FileExistsError(f"Output path {output_path} already exists")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Walk through all files and directories in dir_path
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():  # Skip directories, they're added implicitly
                # Calculate relative path for the archive
                rel_path = file_path.relative_to(dir_path)
                # Prepend the directory name to create the correct structure
                arcname = str(Path(dir_path.name) / rel_path)
                zipf.write(file_path, arcname)

    return output_path


def _generate_main_py(proj_name: str, truffle_manifest: dict[str, Any]) -> str:
    """
    Fill in the main.py template and return
    """
    return f"""
import truffle

class {proj_name}:
    def __init__(self):
        self.metadata = truffle.AppMetadata(
            name="{proj_name}",
            description="{truffle_manifest["description"]}",
            icon="icon.png",
        )
    
    # All tool calls must start with a capital letter! 
    @truffle.tool(
        description="Replace this with a description of the tool.",
        icon="brain"
    )
    @truffle.args(user_input="A description of the argument")
    def {proj_name}Tool(self, user_input: str) -> str:
        \"\"\"
        Replace this text with a basic description of what this function does.
        \"\"\"
        # There are 
        pass

if __name__ == "__main__":
    app = truffle.TruffleApp({proj_name}())
    app.launch()
"""


@cli.command()
def init(
    proj_name: Annotated[
        str,
        typer.Argument(help="The name of your app in PascalCase (e.g. WebsiteFetcher)"),
    ] = ".",
    num_examples: Annotated[
        int,
        typer.Option(
            help="The number of exampleprompts you'd like to log for your App"
        ),
    ] = 5,
):
    """
    Generate a Truffle App project.

    If called with no project name, then assume that it is being called within a folder
    """
    if proj_name == ".":
        proposed_proj_name = Path(proj_name).absolute().name
        typer.confirm(f"Project Name: {proposed_proj_name}", default=True, abort=True)
    # class names and method names need to start with a capital unfortunately, so we enforce this here
    proj_name = str(proj_name)[0].upper() + str(proj_name)[1:]
    proj_path = Path(proj_name)
    if proj_path.exists():
        log.error(f"{proj_name} already exists here on this filesystem")
        sys.exit(-1)
    truffle_manifest: dict[str, Any] = {
        "name": proj_name.lower(),
        "description": typer.prompt("App description: "),
        "example_prompts": [
            typer.prompt(f"Enter example prompt {i + 1} of {num_examples}: ", type=str)
            for i in range(num_examples)
        ],
        "manifest_version": 0,
    }
    main_py_text = _generate_main_py(proj_name, truffle_manifest)
    # create the folder and its contents
    proj_path.mkdir()
    (proj_path / "manifest.json").write_text(json.dumps(truffle_manifest))
    (proj_path / "main.py").write_text(main_py_text)
    (proj_path / "requirements.txt").write_text(f"truffle=={__version__}")
    (proj_path / "manifest.json").write_text(
        json.dumps(truffle_manifest, indent=4, sort_keys=True, ensure_ascii=False)
    )
    shutil.copy2(
        Path(__file__).parent / "cli_assets" / "default_app.png",
        proj_path / "app_icon.png",
    )


def update_pyproject(
    pyproject_path: Path,
    new_name: Optional[str] = None,
    new_description: Optional[str] = None,
) -> None:
    """
    Update the project name and description in pyproject.toml

    Args:
        project_dir: Path to the project directory containing pyproject.toml
        new_name: New name for the project
        new_description: New description for the project

    Raises:
        FileNotFoundError: If pyproject.toml doesn't exist
        KeyError: If project table is missing from pyproject.toml
    """

    if not pyproject_path.exists():
        raise FileNotFoundError(f"No pyproject.toml found in {pyproject_path.parent}")

    # Read existing toml
    with pyproject_path.open("rb") as f:
        pyproject = tomli.load(f)

    if "project" not in pyproject:
        raise KeyError("No [project] table found in pyproject.toml")

    # Update values if provided
    if new_name is not None:
        pyproject["project"]["name"] = new_name

    if new_description is not None:
        pyproject["project"]["description"] = new_description

    # Write updated toml
    with pyproject_path.open("wb") as f:
        tomli_w.dump(pyproject, f)


@cli.command()
def setup(
    app_dir: Annotated[
        str,
        typer.Argument(
            help="Relative or absolute path to the folder containing your app"
        ),
    ] = ".",
    num_examples: Annotated[
        int,
        typer.Option(
            help="The number of exampleprompts you'd like to log for your App"
        ),
    ] = 1,
):
    if app_dir == ".":
        proprosed_proj_name = "".join(
            [
                char
                for char in (str(app_dir)[0].upper() + str(app_dir)[1:])
                if char.isalpha()
            ]
        )
        if not typer.confirm(
            f"Set project name to {proprosed_proj_name}", default=True
        ):
            proprosed_proj_name = typer.prompt("Enter Project Name")
    # class names and method names need to start with a capital unfortunately, so we enforce this here
    proj_name = proprosed_proj_name
    proj_path = Path(app_dir)
    truffle_manifest: dict[str, Any] = {
        "name": proj_name.lower(),
        "description": typer.prompt("App description: "),
        "example_prompts": [
            typer.prompt(f"Enter example prompt {i + 1} of {num_examples}: ", type=str)
            for i in range(num_examples)
        ],
        "manifest_version": 0,
    }
    # update pyproject.toml
    update_pyproject(
        proj_path / "pyproject.toml", proj_name.lower(), truffle_manifest["description"]
    )

    main_py_text = _generate_main_py(proj_name, truffle_manifest)
    (proj_path / "main.py").write_text(main_py_text)
    (proj_path / "manifest.json").write_text(
        json.dumps(truffle_manifest, indent=4, sort_keys=True, ensure_ascii=False)
    )

    pass


@cli.command()
def build(
    app_dir: Annotated[
        str,
        typer.Argument(
            help="Relative or absolute path to the folder containing your app"
        ),
    ] = ".",
    check_files: Annotated[
        bool,
        typer.Option(help="Perform file integrity checks", show_choices=False),
    ] = True,
):
    """
    Bundle a Truffle App project folder into a zip for distribution.
    """
    app_dir = Path(app_dir)
    # Validate the given app dir has a script
    if not app_dir.exists():
        log.error(f"Given path {app_dir} does not exist.")
    elif not check_files or (
        _validate_main_py(app_dir / "main.py")
        and _validate_truffle_json(app_dir / "manifest.json")
        # and _validate_requirements_txt(app_dir / "requirements.txt")
    ):
        _assemble_zip(app_dir.absolute())


# Suppress only the single warning from urllib3 needed.
urllib3.disable_warnings(InsecureRequestWarning)


def send_zip_file(
    url: str, zip_path: Path, user_id: str, filename: Optional[str] = None
) -> Response:
    """
    Send a zip file via POST request, accepting self-signed certificates.

    Args:
        url: The target URL for the POST request
        zip_path: Path to the zip file to send
        user_id: User ID to include as URL parameter
        filename: Optional custom filename for the uploaded file

    Returns:
        Response object from the request
    """

    # Parameters for the request
    params: Dict[str, str] = {"user": user_id}

    # Open and send file
    response = requests.post(
        url, params=params, data=zip_path.read_bytes(), verify=False
    )

    return response


@cli.command()
def upload(
    app_dir: Annotated[
        str,
        typer.Argument(
            help="Relative or absolute path to the folder containing your app"
        ),
    ] = ".",
    check_files: Annotated[
        bool,
        typer.Option(help="Perform file integrity checks", show_choices=False),
    ] = True,
) -> Response:
    """Push a built truffle app to the cloud"""
    url = "https://overcast.itsalltruffles.com:2087"
    user_id = (
        Path(
            f"/Users/{getpass.getuser()}/Library/Containers/com.deepshard.TruffleOS/Data/Library/Application Support/TruffleOS/magic-number.txt"
        )
    ).read_text()
    zip_path = Path(app_dir)

    try:
        response = send_zip_file(url, zip_path, user_id)
        if response.status_code == 200:
            print(f"Upload of {zip_path.name} successful!")

    except FileNotFoundError:
        print(f"Error: Could not find file {zip_path}")
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")

    pass


if __name__ == "__main__":
    cli()
