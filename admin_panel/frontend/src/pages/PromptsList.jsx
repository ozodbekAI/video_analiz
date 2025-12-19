import { DragDropContext, Droppable, Draggable } from "@hello-pangea/dnd";
import { useEffect, useState } from "react";
import { api } from "../api/api";

export default function PromptsList() {
  const [prompts, setPrompts] = useState([]);

  async function load() {
    const r = await api.get("/admin/prompts/");
    setPrompts(r.data.sort((a, b) => a.order - b.order));
  }

  async function onDragEnd(result) {
    if (!result.destination) return;

    const items = Array.from(prompts);
    const [moved] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, moved);

    const reordered = items.map((p, idx) => ({
      ...p,
      order: idx + 1,
    }));

    setPrompts(reordered);

    await api.post("/admin/prompts/reorder", {
      orders: reordered.map(p => ({ id: p.id, order: p.order })),
    });
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold mb-6">🧠 Промпты</h2>

      <DragDropContext onDragEnd={onDragEnd}>
        <Droppable droppableId="prompts">
          {(prov) => (
            <div ref={prov.innerRef} {...prov.droppableProps} className="space-y-3">
              {prompts.map((p, i) => (
                <Draggable key={p.id} draggableId={p.id.toString()} index={i}>
                  {(prov) => (
                    <div
                      ref={prov.innerRef}
                      {...prov.draggableProps}
                      {...prov.dragHandleProps}
                      className="card cursor-move flex justify-between"
                    >
                      <div>
                        <b>{p.name}</b>
                        <div className="text-sm text-gray-500">
                          {p.analysis_type} {p.module_id && `• ${p.module_id}`}
                        </div>
                      </div>
                      <span className="text-gray-400">⇅</span>
                    </div>
                  )}
                </Draggable>
              ))}
              {prov.placeholder}
            </div>
          )}
        </Droppable>
      </DragDropContext>
    </div>
  );
}
