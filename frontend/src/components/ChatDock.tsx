import { useRef, useState, type KeyboardEvent, type ReactNode } from "react";

export const MIN_WIDTH = 320;
export const MAX_WIDTH = 720;
export const DEFAULT_WIDTH = 420;
const KEY_STEP = 24;

export function clampWidth(width: number): number {
  return Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, Math.round(width)));
}

interface Props {
  open: boolean;
  width: number;
  onClose: () => void;
  onResize: (width: number) => void;
  label: string;
  children: ReactNode;
}

/**
 * The chat column. On large screens it is docked to the right of the page,
 * slides closed to give the workspace the full width, and can be resized by
 * dragging its left edge (or with the arrow keys on that edge). On smaller
 * screens it slides in over the page with a backdrop.
 */
export default function ChatDock({
  open,
  width,
  onClose,
  onResize,
  label,
  children,
}: Props) {
  const [dragging, setDragging] = useState(false);
  const drag = useRef<{ startX: number; startWidth: number } | null>(null);

  function onPointerDown(event: React.PointerEvent<HTMLDivElement>) {
    drag.current = { startX: event.clientX, startWidth: width };
    setDragging(true);
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function onPointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!drag.current) return;
    const moved = drag.current.startX - event.clientX;
    onResize(clampWidth(drag.current.startWidth + moved));
  }

  function onPointerUp() {
    drag.current = null;
    setDragging(false);
  }

  function onHandleKey(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowLeft") onResize(clampWidth(width + KEY_STEP));
    else if (event.key === "ArrowRight") onResize(clampWidth(width - KEY_STEP));
    else if (event.key === "Home") onResize(MAX_WIDTH);
    else if (event.key === "End") onResize(MIN_WIDTH);
    else return;
    event.preventDefault();
  }

  return (
    <>
      <div
        aria-hidden="true"
        onClick={onClose}
        className={`fixed inset-0 z-30 bg-slate-900/40 transition-opacity lg:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />
      <aside
        aria-label={label}
        aria-hidden={open ? undefined : true}
        inert={!open}
        data-testid="chat-dock"
        data-open={open}
        style={{ "--chat-width": `${width}px` } as React.CSSProperties}
        className={`fixed inset-y-0 right-0 z-40 w-full max-w-md bg-white shadow-2xl ease-out sm:w-[28rem] lg:sticky lg:top-6 lg:z-0 lg:h-[calc(100vh-7.5rem)] lg:max-w-none lg:shrink-0 lg:translate-x-0 lg:rounded-lg lg:shadow-none ${
          dragging ? "" : "transition-all duration-300"
        } ${
          open
            ? "translate-x-0 lg:w-[var(--chat-width)] lg:opacity-100"
            : "translate-x-full lg:pointer-events-none lg:w-0 lg:opacity-0"
        }`}
      >
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize chat"
          aria-valuemin={MIN_WIDTH}
          aria-valuemax={MAX_WIDTH}
          aria-valuenow={width}
          tabIndex={0}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onKeyDown={onHandleKey}
          onDoubleClick={() => onResize(DEFAULT_WIDTH)}
          title="Drag to resize. Double-click to reset."
          className="group absolute inset-y-0 -left-3 z-10 hidden w-3 cursor-col-resize touch-none items-center justify-center focus-visible:outline-none lg:flex"
        >
          <span
            className={`h-16 w-1.5 rounded-full transition ${
              dragging
                ? "bg-indigo-500"
                : "bg-slate-300 group-hover:bg-indigo-400 group-focus-visible:bg-indigo-500"
            }`}
          />
        </div>
        <div className="h-full overflow-hidden lg:rounded-lg lg:border lg:border-slate-200">
          {children}
        </div>
      </aside>
    </>
  );
}
