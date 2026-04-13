import { useAuth } from "../auth/AuthContext";
import type { ListType, MinerviniRow } from "../types";

type Props = {
  row: MinerviniRow | null;
  saving: boolean;
  disabled?: boolean;
  onChangeListType: (row: MinerviniRow, nextType: ListType | null) => void;
};

const OPTIONS: Array<{ label: string; value: ListType | null }> = [
  { label: "Focus", value: "focus" },
  { label: "Action", value: "action" },
  { label: "Pass", value: "pass" },
  { label: "Clear", value: null },
];

export default function QuickListTypeBar({ row, saving, disabled = false, onChangeListType }: Props) {
  const { checked, isEditor } = useAuth();
  const canEdit = checked && isEditor && Boolean(row) && !disabled && !saving;

  return (
    <section className="quick-list-bar no-export" aria-label="Quick list type actions">
      <div className="quick-list-shell">
        <div className="quick-list-meta">
          <span className="quick-list-label">Quick List Type</span>
          <p className="quick-list-help">
            {row ? `Selected: ${row.ticker} · ${row.market} · ${row.name ?? "-"}` : "Select a ticker from the Minervini list."}
          </p>
        </div>
        <div className="quick-list-buttons">
          {OPTIONS.map((option) => {
            const isActive = (row?.list_type ?? null) === option.value;
            return (
              <button
                key={option.label}
                type="button"
                className={`quick-list-button${isActive ? " active" : ""}`}
                onClick={() => row && onChangeListType(row, option.value)}
                disabled={!canEdit}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
