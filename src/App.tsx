import { ReactFlowProvider } from '@xyflow/react';
import MindMapEditor from './components/MindMapEditor';

export default function App() {
  return (
    <ReactFlowProvider>
      <MindMapEditor />
    </ReactFlowProvider>
  );
}
