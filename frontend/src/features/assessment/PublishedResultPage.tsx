/**
 * Old link target for a single published result. Published marks and grades
 * are shown on the Student overview, so this sends the reader there.
 */

import { Navigate } from "react-router-dom";

export function PublishedResultPage() {
  return <Navigate to="/registry/overview" replace />;
}
