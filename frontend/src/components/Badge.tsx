export default function Badge({ text }: { text: string | null | undefined }) {
  if (!text) return <span className="badge">Unknown</span>;
  const cls = `badge badge-${text.toLowerCase()}`;
  return <span className={cls}>{text.replace(/_/g, " ")}</span>;
}
