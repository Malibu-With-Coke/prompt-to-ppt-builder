import { Outlet } from 'react-router-dom';
import Header from './Header';
import Footer from './Footer';

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col w-full selection:bg-primary-fixed selection:text-primary-container">
      <Header />
      <div className="flex-1 w-full bg-mesh flex flex-col items-center justify-start">
        <Outlet />
      </div>
      <Footer />
    </div>
  );
}
