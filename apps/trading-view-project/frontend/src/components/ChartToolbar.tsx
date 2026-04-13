import type { TimeRangePreset } from "../types";

type ToggleOption = {
  label: string;
  active: boolean;
  onToggle: () => void;
};

type Props = {
  title?: string;
  presets?: readonly TimeRangePreset[];
  activePreset?: TimeRangePreset;
  onSelectPreset?: (preset: TimeRangePreset) => void;
  toggles?: ToggleOption[];
};

export default function ChartToolbar({ title, presets = [], activePreset, onSelectPreset, toggles = [] }: Props) {
  const hasPresets = presets.length > 0 && onSelectPreset;
  const hasToggles = toggles.length > 0;

  if (!hasPresets && !hasToggles) return null;

  return (
    <section className="chart-toolbar no-export" aria-label={title ?? "Chart controls"}>
      {title ? <span className="chart-toolbar-title">{title}</span> : null}
      {hasPresets ? (
        <div className="chart-toolbar-group">
          {presets.map((preset) => (
            <button
              key={preset}
              type="button"
              className={`chart-toolbar-button${activePreset === preset ? " active" : ""}`}
              aria-pressed={activePreset === preset}
              onClick={() => onSelectPreset(preset)}
            >
              {preset}
            </button>
          ))}
        </div>
      ) : null}
      {hasToggles ? (
        <div className="chart-toolbar-group chart-toolbar-group-right">
          {toggles.map((toggle) => (
            <button
              key={toggle.label}
              type="button"
              className={`chart-toolbar-button${toggle.active ? " active" : ""}`}
              aria-pressed={toggle.active}
              onClick={toggle.onToggle}
            >
              {toggle.label}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
