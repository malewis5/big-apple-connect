import InfoPageView, { infoMetadata } from "../info-page";

export const metadata = infoMetadata("contact");

export default function Page() {
  return <InfoPageView slug="contact" />;
}
