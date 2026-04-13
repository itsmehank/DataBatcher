import { useEffect, useRef } from "react";
import { useAuth } from "../auth/AuthContext";
import type { ListType, MinerviniRow } from "../types";

type Props = {
  rows: MinerviniRow[];
  selectedSymbol: string;
  checkedKeys: Record<string, boolean>;
  areAllRowsChecked: boolean;
  areSomeRowsChecked: boolean;
  onSelectTicker: (ticker: string) => void;
  onToggleRowChecked: (row: MinerviniRow) => void;
  onToggleAllChecked: () => void;
  onChangeListType: (row: MinerviniRow, listType: ListType | null) => void;
  savingKeys: Record<string, boolean>;
  disableSelection?: boolean;
};

const getRowKey = (row: MinerviniRow) => `${row.ticker}:${row.market}`;

export default function MinerviniTable({
  rows,
  selectedSymbol,
  checkedKeys,
  areAllRowsChecked,
  areSomeRowsChecked,
  onSelectTicker,
  onToggleRowChecked,
  onToggleAllChecked,
  onChangeListType,
  savingKeys,
  disableSelection = false,
}: Props) {
  const { isEditor } = useAuth();
  const headerCheckboxRef = useRef<HTMLInputElement | null>(null);
  const tableWrapRef = useRef<HTMLDivElement | null>(null);
  const activeRowRef = useRef<HTMLTableRowElement | null>(null);

  useEffect(() => {
    if (!headerCheckboxRef.current) return;
    headerCheckboxRef.current.indeterminate = areSomeRowsChecked;
  }, [areSomeRowsChecked]);

  useEffect(() => {
    if (!selectedSymbol || !tableWrapRef.current || !activeRowRef.current) return;

    const wrapper = tableWrapRef.current;
    const row = activeRowRef.current;
    const rowTop = row.offsetTop;
    const rowBottom = rowTop + row.offsetHeight;
    const viewTop = wrapper.scrollTop;
    const viewBottom = viewTop + wrapper.clientHeight;

    if (rowTop < viewTop) {
      wrapper.scrollTo({ top: rowTop, behavior: "smooth" });
      return;
    }

    if (rowBottom > viewBottom) {
      wrapper.scrollTo({ top: rowBottom - wrapper.clientHeight, behavior: "smooth" });
    }
  }, [selectedSymbol, rows]);

  return (
    <section className="panel table-panel">
      <div className="panel-header">
        <h2>Minervini Template List</h2>
        <span>{rows.length} rows</span>
      </div>
      <div ref={tableWrapRef} className="table-wrap">
        <table>
          <thead>
            <tr>
              <th className="checkbox-cell">
                <input
                  ref={headerCheckboxRef}
                  type="checkbox"
                  aria-label="Select all rows for download"
                  checked={areAllRowsChecked}
                  onChange={() => onToggleAllChecked()}
                  disabled={disableSelection || rows.length === 0}
                />
              </th>
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
              <tr
                key={`${row.ticker}-${row.market}`}
                ref={row.ticker === selectedSymbol ? activeRowRef : null}
                className={row.ticker === selectedSymbol ? "active" : ""}
              >
                <td className="checkbox-cell">
                  <input
                    type="checkbox"
                    aria-label={`Select ${row.ticker} for download`}
                    checked={Boolean(checkedKeys[getRowKey(row)])}
                    onChange={() => onToggleRowChecked(row)}
                    disabled={disableSelection}
                  />
                </td>
                <td>
                  <button className="link-button" onClick={() => onSelectTicker(row.ticker)} disabled={disableSelection}>
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
