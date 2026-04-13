import type { ListType, Region } from "../types";

type Props = {
  region: Region;
  date: string;
  market: string;
  listCategory: ListType | "all";
  className?: string;
  disabled?: boolean;
  regions: Region[];
  dates: string[];
  markets: string[];
  onChange: (key: "region" | "date" | "market" | "listCategory", value: string) => void;
};

function SelectField({
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="filter-item">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function FilterBar(props: Props) {
  const className = props.className ? `filter-bar ${props.className}` : "filter-bar";
  return (
    <section className={className}>
      <SelectField
        label="Region"
        value={props.region}
        options={props.regions}
        disabled={props.disabled}
        onChange={(value) => props.onChange("region", value)}
      />
      <SelectField
        label="Date"
        value={props.date}
        options={props.dates}
        disabled={props.disabled}
        onChange={(value) => props.onChange("date", value)}
      />
      <SelectField
        label="Market"
        value={props.market}
        options={props.markets}
        disabled={props.disabled}
        onChange={(value) => props.onChange("market", value)}
      />
      <SelectField
        label="List Type"
        value={props.listCategory}
        options={["all", "focus", "action", "pass"]}
        disabled={props.disabled}
        onChange={(value) => props.onChange("listCategory", value)}
      />
    </section>
  );
}
