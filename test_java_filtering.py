#!/usr/bin/env python3
"""
Java Filtering Test Script
=========================

This script tests the new Java internal package filtering functionality
to ensure that only application code hotspots are reported.
"""

import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from comparison.csv_comparison_engine import CSVComparisonEngine
    from comparison.line_by_line_comparator import LineByLineComparator
    
    def test_java_filtering():
        """Test the Java filtering functionality."""
        
        print("🧪 Testing Java Internal Package Filtering")
        print("=" * 60)
        
        # Initialize components
        engine = CSVComparisonEngine()
        comparator = LineByLineComparator()
        
        # Test cases
        test_cases = [
            # Java internal packages (should be filtered)
            ('java.awt.EventQueue.dispatchEventImpl()', True, 'Java AWT'),
            ('javax.swing.Timer.run()', True, 'Java Swing'),
            ('java.security.AccessController.doPrivileged()', True, 'Java Security'),
            ('sun.security.provider.SecureRandom()', True, 'Sun Internal'),
            ('com.sun.internal.Something()', True, 'Sun Internal'),
            ('jdk.internal.reflection.NativeMethodAccessorImpl()', True, 'JDK Internal'),
            ('oracle.jdbc.driver.OracleDriver()', True, 'Oracle Internal'),
            ('com.oracle.graal.Something()', True, 'Oracle Graal'),
            
            # Application code (should be kept)
            ('com.mycompany.myapp.service.UserService.processUser()', False, 'Application Code'),
            ('org.springframework.boot.Application.run()', False, 'Spring Framework'),
            ('chs.caf.caplet.helpers.EventDistributorHelper.accept()', False, 'CHS Application'),
            ('net.sf.ehcache.Cache.get()', False, 'Third-party Library'),
            ('org.apache.commons.lang.StringUtils.isBlank()', False, 'Apache Commons'),
        ]
        
        print("1. Testing CSV Comparison Engine filtering...")
        print("   (❌ = Filtered out, ✅ = Kept for analysis)")
        
        engine_correct = 0
        for function_name, should_filter, description in test_cases:
            is_filtered = engine._is_java_internal_line(function_name)
            status = "❌ FILTERED" if is_filtered else "✅ KEPT"
            correct = "✓" if is_filtered == should_filter else "✗"
            print(f"   {status} {function_name} ({description}) {correct}")
            if is_filtered == should_filter:
                engine_correct += 1
        
        print(f"\n   Engine Results: {engine_correct}/{len(test_cases)} correct")
        
        print("\n2. Testing Line-by-Line Comparator filtering...")
        comparator_correct = 0
        for function_name, should_filter, description in test_cases:
            is_filtered = comparator._is_java_internal_line(function_name)
            status = "❌ FILTERED" if is_filtered else "✅ KEPT"
            correct = "✓" if is_filtered == should_filter else "✗"
            print(f"   {status} {function_name} ({description}) {correct}")
            if is_filtered == should_filter:
                comparator_correct += 1
        
        print(f"\n   Comparator Results: {comparator_correct}/{len(test_cases)} correct")
        
        # Overall results
        total_correct = engine_correct + comparator_correct
        total_tests = len(test_cases) * 2
        
        print(f"\n📊 Overall Test Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {total_correct}")
        print(f"   Success Rate: {(total_correct/total_tests)*100:.1f}%")
        
        if total_correct == total_tests:
            print(f"\n🎉 ALL TESTS PASSED!")
            print(f"   ✅ Java internal packages will be filtered out")
            print(f"   ✅ Application code will be analyzed")
            print(f"   ✅ AI analysis will focus on actionable hotspots")
            return True
        else:
            print(f"\n⚠️  Some tests failed - filtering may need adjustment")
            return False
    
    def demonstrate_impact():
        """Demonstrate the impact of Java filtering."""
        
        print(f"\n🎯 Impact Demonstration")
        print("=" * 60)
        
        print("Before filtering (typical analysis):")
        print("   1. java.awt.EventDispatchThread.run() +64965ms")
        print("   2. java.awt.EventQueue.dispatchEvent() +50254ms") 
        print("   3. java.security.AccessController.doPrivileged() +51161ms")
        print("   4. javax.swing.Timer.run() +12000ms")
        print("   5. com.mycompany.service.UserService.processUser() +5000ms")
        print("   ...")
        print("   → Analysis dominated by Java internals (not actionable)")
        
        print(f"\nAfter filtering (improved analysis):")
        print("   1. com.mycompany.service.UserService.processUser() +5000ms")
        print("   2. org.myapp.controller.OrderController.processOrder() +3200ms")
        print("   3. chs.caf.caplet.helpers.EventDistributorHelper.accept() +2100ms")
        print("   4. net.mycompany.dao.UserRepository.findById() +1800ms")
        print("   5. com.myapp.util.ValidationUtils.validateInput() +1200ms")
        print("   ...")
        print("   → Analysis focused on actionable application code!")
        
        print(f"\n✨ Benefits:")
        print("   🎯 Hotspot detection focuses on your code")
        print("   ⚡ Faster analysis (less noise to process)")
        print("   🔧 Actionable recommendations only") 
        print("   📊 Better signal-to-noise ratio")
        print("   🚀 More relevant AI insights")

    if __name__ == "__main__":
        success = test_java_filtering()
        demonstrate_impact()
        
        if success:
            print(f"\n🚀 Java Filtering Feature Ready!")
            print(f"   The application will now filter out Java internal packages")
            print(f"   and focus analysis on your application code.")
            print(f"   Start the app: streamlit run src/streamlit_app.py")
        else:
            print(f"\n⚠️  Please check the filtering logic")
        
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)
except Exception as e:
    print(f"❌ Test error: {e}")
    sys.exit(1)
