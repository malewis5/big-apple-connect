import InfoPageView, { infoMetadata } from "../info-page";

export const metadata = infoMetadata("privacy");

export default function Page() {
  return <InfoPageView slug="privacy" />;
}
