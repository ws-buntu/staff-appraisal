export default function Page() {
  return (
    <main>
      <p className="eyebrow">Performance planning, review & appraisal</p>
      <h1>Staff Appraisal</h1>
      <p className="intro">A clear place to plan goals, review progress and recognise contributions.</p>
      <section aria-labelledby="foundation-heading">
        <p role="status" className="status">Foundation in progress</p>
        <h2 id="foundation-heading">The starting point is ready for development.</h2>
        <p>Staff accounts, appraisal forms and review workflows are planned. They are not available yet.</p>
        <p>No staff records or appraisal results are displayed here.</p>
      </section>
      <aside aria-labelledby="scoring-heading">
        <h2 id="scoring-heading">Scoring requires confirmation</h2>
        <p>The final overall-score formula remains unresolved. Overall ratings and promotion decisions will not be calculated until authoritative guidance is verified.</p>
      </aside>
      <footer>Sprint 4.7 · Task 1 · Application foundation</footer>
    </main>
  );
}
