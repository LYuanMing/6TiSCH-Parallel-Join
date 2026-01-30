# Development  

To make sure all the function can work well, the modification in this project should have corresponding test function.

## Setup with Pytest

After installing all the required packet, and the simulator can be executed successfully. Then we can run pytest before the development

### Command line

Enter the root directory of this project, you can see *tests* directory. And execute the command below to start the tests

```
pytest -s -x -vv tests
```

There are also some tests in gui, but something wrong I am not sure in these tests. You may fail in these tests even the simulation engine can run successfully. If you need to run all tests in this project, you can remove *tests* in above command.

### VScode Configuration

For vscode, you can also configure the Run And Debug in launch.json with following content:

```json
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug runSim.py (full path)",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/bin/runSim.py",
            "console": "integratedTerminal",
            "justMyCode": true,
            "cwd": "${workspaceFolder}",
            "args": [
                "--config=${workspaceFolder}/bin/config.json"
            ]
        },
        {
            "name": "Debug all tests (pytest)",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "justMyCode": true,
            "env": {
                "GEVENT_SUPPORT": "True"
            },
            "args": [
                "-s",
                "-vv",
                "tests"
            ]
        },
        {
            "name": "Debug pytest current test file",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "justMyCode": true,
            "env": {
                "GEVENT_SUPPORT": "True"
            },
            "args": [
                "-s",
                "-x",
                "-vv",
                "${relativeFile}",
            ],
        },
        {
            "name": "Debug pytest current test function",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "justMyCode": true,
            "env": {
                "GEVENT_SUPPORT": "True"
            },
            "args": [
                "-s",
                "-x",
                "-vv",
                "${relativeFile}::${selectedText}"
            ]
        }
    ]
}
```

In VScode, you may find that there are some breaks while running pytest in some tests. The exception is raised by *sys.exit(1)* in *print_error_and_exit*. Don't worry, just continue the tests, it is the normal cases.

