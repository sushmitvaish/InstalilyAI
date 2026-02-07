import "./App.css";
import ChatWindow from "./components/ChatWindow";

function App() {
  return (
    <div className="App">
      <div className="heading">
        <span className="heading-icon">&#9881;</span>
        PartSelect Assistant
      </div>
      <ChatWindow />
    </div>
  );
}

export default App;
