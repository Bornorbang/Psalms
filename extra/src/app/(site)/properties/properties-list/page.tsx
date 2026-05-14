import AdvanceSearch from "@/app/components/property-list/search";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Properties List",
};

export const dynamic = "force-static";

const Page = () => {
  return (
    <>
      <AdvanceSearch />
    </>
  );
};

export default Page;
