import { useAuth } from "../auth/AuthContext";
import type { ListType, MinerviniRow } from "../types";

type Props = {
  rows: MinerviniRow[];
  selectedSymbol: string;
  onSelectTicker: (ticker: string) => void;
  onChangeListType: (row: MinerviniRow, listType: ListType | null) => void;
  savingKeys: Record<string, boolean>;
};

export default function MinerviniTable({ rows, selectedSymbol, onSelectTicker, onChangeListType, savingKeys }: Props) {
  const { isEditor } = useAuth();
  return (
    <section className="panel table-panel">
      <div className="panel-header">
        <h2>Minervini Template List</h2>
        <span>{rows.length} rows</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Name</th>
              <th>Market</th>
              <th>Sector</th>
              <th>RS Rating</th>
              <th>Blue Dot</th>
              <th>List Type</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.ticker}-${row.market}`} className={row.ticker === selectedSymbol ? "active" : ""}>
                <td>
                  <button className="link-button" onClick={() => onSelectTicker(row.ticker)}>
                    {row.ticker}
                  </button>
                </td>
                <td>{row.name ?? "-"}</td>
                <td>{row.market}</td>
                <td>{row.sector ?? "-"}</td>
                <td className="rs-cell">{row.rs_rating ?? "-"}</td>
                <td>{row.is_blue_dot === 1 ? "BLUE" : ""}</td>
                <td>
                  <select
                    value={row.list_type ?? ""}
                    onChange={(e) => onChangeListType(row, (e.target.value || null) as ListType | null)}
                    disabled={!isEditor || savingKeys[`${row.ticker}:${row.market}`]}
                  >
                    <option value="">(none)</option>
                    <option value="focus">focus</option>
                    <option value="action">action</option>
                    <option value="pass">pass</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
