import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="bg-slate-100 dark:bg-[#000613] py-12 px-8 w-full mt-auto">
      <div className="flex flex-col md:flex-row justify-between items-center max-w-7xl mx-auto gap-8">
        <div className="flex flex-col items-center md:items-start gap-2">
          <span className="text-sm font-semibold text-slate-900 dark:text-gray-200 font-headline">ArchitectEditor</span>
          <p className="text-xs text-slate-500">© 2024 Architectural Editor. All rights reserved.</p>
        </div>
        <nav className="flex flex-wrap justify-center gap-8">
          <Link to="#" className="text-slate-500 text-sm font-medium hover:text-[#001f3f] dark:hover:text-white transition-colors">Privacy Policy</Link>
          <Link to="#" className="text-slate-500 text-sm font-medium hover:text-[#001f3f] dark:hover:text-white transition-colors">Terms of Service</Link>
          <Link to="#" className="text-slate-500 text-sm font-medium hover:text-[#001f3f] dark:hover:text-white transition-colors">Security</Link>
          <Link to="#" className="text-slate-500 text-sm font-medium hover:text-[#001f3f] dark:hover:text-white transition-colors">Help Center</Link>
        </nav>
      </div>
    </footer>
  );
}
