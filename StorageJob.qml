import Quickshell.Io

// argv and environment never contain notification payloads or image paths.
Process {
  id: root
  property string helperPath: ""
  property string stateDirectory: ""
  property string action: "repair"
  property var payload: ({})
  command: ["python3", helperPath, action, stateDirectory]
  stdinEnabled: true
  onStarted: write(JSON.stringify(payload) + "\n")
}
