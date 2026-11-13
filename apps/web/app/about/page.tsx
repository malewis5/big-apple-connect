import InfoPageView, { infoMetadata } from "../info-page";

export const metadata = infoMetadata("about");

export default function Page() {
  return <InfoPageView slug="about" />;
}
