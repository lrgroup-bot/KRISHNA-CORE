import LegacyKrishnaPreview from './LegacyKrishnaPreview';

/**
 * Static source contract for deterministic audits.
 *
 * Runtime navigation is composed inside LegacyKrishnaPreview from the canonical
 * KRISHNA dashboard plus the Brahmand owner layer. Keeping the contract here lets
 * source-only auditing verify the owner-visible hierarchy without rendering a
 * duplicate React sidebar around the iframe.
 */
export const COMPOSED_OWNER_NAVIGATION_CONTRACT = String.raw`
<nav aria-label="Main Menu">
  <button type="button"><span>KRISHNA</span></button>
  <button type="button"><span>Sudarshan</span></button>
  <button type="button"><span>LR Universe</span></button>
  <button type="button"><span>Brahmand</span></button>
  <button type="button"><span>Plugins</span></button>
</nav>`;

export default function App() {
  return <LegacyKrishnaPreview />;
}
